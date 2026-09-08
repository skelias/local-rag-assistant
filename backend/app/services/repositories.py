"""Repository 层：每个表配一个"管理员"，业务代码不直接写 SQL。

好处：
- SQL 集中在一处，别处只调用"管理员方法"；
- 测试容易：给管理员一个临时数据库即可；
- 将来换 PostgreSQL：只改这里的实现，调用方不用动。
"""
import json
from typing import Any

from app.models.database import Database
from app.models.schemas import DocumentCreate, MessageCreate


def _json(v: Any) -> str:
    """把 Python 对象转成 JSON 字符串（存进数据库 TEXT 列）。"""
    return json.dumps(v, ensure_ascii=False)


def _loads(s: str | None, default: Any = None) -> Any:
    """把数据库里的 JSON 字符串还原成 Python 对象；空值返回 default。"""
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        return default


class ConversationRepository:
    """对话表的"管理员"：建对话、存消息、读历史、列会话、删会话。"""

    def __init__(self, db: Database):
        self.db = db

    async def create(self, title: str, model: str | None, kb_id: int = 1) -> int:
        """新建一场对话，返回它的 id。"""
        cur = await self.db.conn.execute(
            "INSERT INTO conversations(kb_id,title,model) VALUES(?,?,?)",
            (kb_id, title, model),
        )
        await self.db.conn.commit()
        return cur.lastrowid

    async def save_message(self, conv_id: int, msg: MessageCreate) -> int:
        """往某场对话里存一条消息，返回消息 id。sources 会存成 JSON 字符串。"""
        cur = await self.db.conn.execute(
            "INSERT INTO messages(conv_id,role,content,sources) VALUES(?,?,?,?)",
            (conv_id, msg.role, msg.content, _json(msg.sources)),
        )
        await self.db.conn.commit()
        return cur.lastrowid

    async def get_messages(self, conv_id: int, limit: int = 100) -> list[dict]:
        """按时间顺序返回某场对话最近 limit 条消息（sources 还原成列表）。"""
        cur = await self.db.conn.execute(
            "SELECT * FROM messages WHERE conv_id=? ORDER BY id DESC LIMIT ?",
            (conv_id, limit),
        )
        rows = await cur.fetchall()
        rows.reverse()  # DESC 查出来后倒过来 = 时间正序
        return [dict(r) | {"sources": _loads(r["sources"], [])} for r in rows]

    async def list(self, kb_id: int = 1) -> list[dict]:
        """列出某知识库下的会话（新的在前）。"""
        cur = await self.db.conn.execute(
            "SELECT * FROM conversations WHERE kb_id=? ORDER BY id DESC LIMIT 100",
            (kb_id,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def delete(self, conv_id: int) -> None:
        """删除一场对话（消息会被外键 ON DELETE CASCADE 自动带走）。"""
        await self.db.conn.execute("DELETE FROM conversations WHERE id=?", (conv_id,))
        await self.db.conn.commit()


class DocumentRepository:
    """文档表的"管理员"：登记文档、改状态、查列表。"""

    def __init__(self, db: Database):
        self.db = db

    async def create(self, doc: DocumentCreate) -> int:
        """登记一份上传的文档，返回 id。初始状态 uploading。"""
        cur = await self.db.conn.execute(
            "INSERT INTO documents(kb_id,filename,file_type,file_path,size) VALUES(?,?,?,?,?)",
            (doc.kb_id, doc.filename, doc.file_type, doc.file_path, doc.size),
        )
        await self.db.conn.commit()
        return cur.lastrowid

    async def get(self, doc_id: int) -> dict | None:
        """按 id 查文档；不存在返回 None。"""
        cur = await self.db.conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,))
        r = await cur.fetchone()
        return dict(r) if r else None

    async def set_status(self, doc_id: int, status: str, error: str | None = None) -> None:
        """改文档状态（uploading→parsed→ready/failed），顺带记时间。"""
        await self.db.conn.execute(
            "UPDATE documents SET status=?, error=?, updated_at=datetime('now','localtime') WHERE id=?",
            (status, error, doc_id),
        )
        await self.db.conn.commit()

    async def list_by_kb(self, kb_id: int) -> list[dict]:
        """列出某知识库的文档；附带一个 chunk_count（已入向量库的分块数）。"""
        cur = await self.db.conn.execute(
            "SELECT d.*, "
            "(SELECT COUNT(*) FROM chunks c WHERE c.document_id=d.id AND c.status='indexed') AS chunk_count "
            "FROM documents d WHERE d.kb_id=? ORDER BY d.id DESC",
            (kb_id,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def delete(self, doc_id: int) -> None:
        """删除文档记录（chunks 由外键 ON DELETE CASCADE 自动清掉）。"""
        await self.db.conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        await self.db.conn.commit()


class ChunkRepository:
    """分块表的"管理员"：写入块、按文档取块、标记已索引。"""

    def __init__(self, db: Database):
        self.db = db

    async def delete_by_document(self, doc_id: int) -> None:
        """删掉某文档的全部旧分块（重新解析前先清场）。"""
        await self.db.conn.execute("DELETE FROM chunks WHERE document_id=?", (doc_id,))
        await self.db.conn.commit()

    async def insert_many(self, items: list[dict]) -> None:
        """批量插入分块。items 元素：{kb_id, document_id, seq, text, meta}。"""
        await self.db.conn.executemany(
            "INSERT INTO chunks(kb_id,document_id,seq,text,meta,status) "
            "VALUES(:kb_id,:document_id,:seq,:text,:meta,:status)",
            [
                {**i,
                 "meta": _json(i.get("meta", {})),          # meta 字典 → JSON 字符串
                 "status": i.get("status", "pending")}
                for i in items
            ],
        )
        await self.db.conn.commit()

    async def _fetch(self, sql: str, params: tuple) -> list[dict]:
        cur = await self.db.conn.execute(sql, params)
        rows = await cur.fetchall()
        # meta 是 JSON 字符串，读回时还原成字典
        return [dict(r) | {"meta": _loads(r["meta"], {})} for r in rows]

    async def list_pending(self, doc_id: int) -> list[dict]:
        """取某文档还没入向量库的分块（供"分段预览"和"确认入库"用）。"""
        return await self._fetch(
            "SELECT * FROM chunks WHERE document_id=? AND status='pending' ORDER BY seq",
            (doc_id,),
        )

    async def list_all(self, doc_id: int) -> list[dict]:
        """取某文档全部分块（不挑状态）。"""
        return await self._fetch(
            "SELECT * FROM chunks WHERE document_id=? ORDER BY seq",
            (doc_id,),
        )

    async def mark_indexed(self, doc_id: int) -> None:
        """把某文档所有块标记为已入向量库（status='indexed'）。"""
        await self.db.conn.execute(
            "UPDATE chunks SET status='indexed' WHERE document_id=?", (doc_id,)
        )
        await self.db.conn.commit()


class ConfigRepository:
    """设置表的"管理员"：键值对读写，值用 JSON 编码。"""

    def __init__(self, db: Database):
        self.db = db

    async def get(self, key: str, default: Any = None) -> Any:
        """读一个设置；没设置过时返回 default。"""
        cur = await self.db.conn.execute(
            "SELECT value FROM user_config WHERE key=?", (key,)
        )
        r = await cur.fetchone()
        return _loads(r["value"], default) if r else default

    async def set(self, key: str, value: Any) -> None:
        """写一个设置；键已存在则覆盖（ON CONFLICT DO UPDATE）。"""
        await self.db.conn.execute(
            "INSERT INTO user_config(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, _json(value)),
        )
        await self.db.conn.commit()

    async def all(self) -> dict[str, Any]:
        """把所有设置倒出来（设置页/启动时读配置用）。"""
        cur = await self.db.conn.execute("SELECT key,value FROM user_config")
        return {r["key"]: _loads(r["value"]) for r in await cur.fetchall()}


class UsageRepository:
    """用量表的"管理员"：记一次调用消耗（token + 缓存命中），算总计与命中率。"""

    def __init__(self, db: Database):
        self.db = db

    async def record(self, model: str, out_tokens: int = 0,
                     hit_tokens: int = 0, miss_tokens: int = 0) -> None:
        """记一笔：模型、输出 token、缓存命中/未命中输入 token。"""
        await self.db.conn.execute(
            "INSERT INTO usage_records(model,output_tokens,cache_hit_tokens,cache_miss_tokens) "
            "VALUES(?,?,?,?)",
            (model, out_tokens, hit_tokens, miss_tokens),
        )
        await self.db.conn.commit()

    async def summary(self) -> dict:
        """统计：次数、输出 token、缓存命中/未命中、总输入、缓存命中率。
        命中率 = 命中 / (命中 + 未命中)；没有输入时记 0。"""
        cur = await self.db.conn.execute(
            "SELECT COUNT(*) AS requests, "
            "COALESCE(SUM(output_tokens),0) AS output_tokens, "
            "COALESCE(SUM(cache_hit_tokens),0) AS cache_hit_tokens, "
            "COALESCE(SUM(cache_miss_tokens),0) AS cache_miss_tokens "
            "FROM usage_records"
        )
        r = await cur.fetchone()
        d = dict(r) if r else {"requests": 0, "output_tokens": 0,
                               "cache_hit_tokens": 0, "cache_miss_tokens": 0}
        total_in = d["cache_hit_tokens"] + d["cache_miss_tokens"]
        d["input_tokens"] = total_in
        d["cache_hit_rate"] = round(d["cache_hit_tokens"] / total_in, 4) if total_in else 0.0
        return d
