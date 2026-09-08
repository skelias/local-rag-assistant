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
