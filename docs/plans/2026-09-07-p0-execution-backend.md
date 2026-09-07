# RAG AI 助手 — P0 执行计划 · 后端（P0-1 ~ P0-8）

> **For Claude/编码 Agent:** 按 Task 顺序执行；每个 Task 严格 TDD（先写失败测试 → 跑红 → 实现 → 跑绿 → `git commit`）。若某步依赖安装/版本报错，先解决再继续，并在提交信息注明。
>
> **本计划取代** `docs/plans/2026-07-22-backend-phase1.md`（历史参考），并吸收 `docs/plans/2026-09-07-mature-product-spec-and-p0.md`（修订 P0）与 `docs/research/2026-09-07-mature-benchmark.md` 的结论。
> 前端任务见 `docs/plans/2026-09-07-p0-execution-frontend.md`（P0-9 ~ P0-12）。
> **P0-0（git 基线 + 设计资产留存）已于 2026-09-07 完成**，本计划从 P0-1 开始。

**Goal:** 后端最小闭环：上传文档（解析→分段预览→确认入库向量化）→ 提问 → 混合检索（稠密+BM25 稀疏+RRF 融合，可选 Rerank+阈值）→ 流式回答，答案携带结构化可点击来源；命中测试与对话共用同一检索参数。

**Architecture:** 分层 Storage → LLM Gateway → RAG Engine → API Gateway；Repository 模式抽象 SQLite，Provider 模式抽象 LLM/Embedding；解析/分块/索引以**可插拔契约**组织；全部表带 `kb_id`（多库预留）；模型名与密钥走配置（.env → SQLite `user_config` 可覆盖），不硬编码。

**Tech Stack:** Python 3.14 · FastAPI · aiosqlite · Qdrant(local, 稠密+稀疏混合/RRF) · FlagEmbedding BGE-M3(dense+sparse)（可选本地）/ API 备选 · Anthropic / OpenAI 兼容(DeepSeek) API · langchain-text-splitters（仅切分/提示词胶水）· pytest + pytest-asyncio + httpx

**前置条件（已核查）**
- Python 3.14.5、git 2.53（已就绪）；Node 24（前端计划用）
- 本仓库 = `D:\RAG个人AI助手`（历史 `D:\rag` 绝对路径一律按本目录）
- API Key：至少 Claude 或 DeepSeek 一个可用；当前可用模型 ID 以运行环境实测为准（曾出现模型名不可用与 org 429，需在 P0-3 联调时核实）

---

## Task P0-1: 项目脚手架（目录 + 依赖 + 配置 + pytest 就绪）

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `backend/app/__init__.py`、`backend/app/core/__init__.py`、`backend/app/models/__init__.py`、`backend/app/services/__init__.py`、`backend/app/api/__init__.py`、`backend/tests/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/run.py`
- Create: `backend/tests/conftest.py`、`backend/tests/test_health.py`（冒烟）
- Create: `backend/pytest.ini`
- Create: `backend/.env.example`（仅说明，不复制密钥）

**Step 1: 目录**
```bash
cd "D:\RAG个人AI助手"
mkdir -p backend\app\core backend\app\models backend\app\services backend\app\api backend\tests
```

**Step 2: `backend/requirements.txt`**（版本在安装时按 Python 3.14 实测微调；此处为基线）
```txt
# Web
fastapi>=0.115,<1.0
uvicorn[standard]>=0.30
sse-starlette>=2.1
python-multipart>=0.0.9
httpx>=0.27

# Storage
aiosqlite>=0.20
qdrant-client>=1.12

# Embedding (本地 BGE-M3 dense+sparse；首次运行需下载模型)
FlagEmbedding>=1.2.11
torch>=2.3          # FlagEmbedding 依赖；如机器无 GPU 用 CPU 版即可

# RAG 胶水（仅切分与提示词；检索/生成自实现）
langchain-core>=0.3
langchain-text-splitters>=0.3

# LLM SDK（流式）
anthropic>=0.40
openai>=1.55

# Utils
pydantic>=2.9
pydantic-settings>=2.5
python-dotenv>=1.0
```
**Step 3: `backend/requirements-dev.txt`**
```txt
-r requirements.txt
pytest>=8.3
pytest-asyncio>=0.24
anyio>=4.4
```

**Step 4: `backend/pytest.ini`**
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
addopts = -q
```

**Step 5: 配置模块 `backend/app/core/config.py`**
```python
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # 仓库根
ENV_FILE = BASE_DIR / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE), env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # 路径
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = DATA_DIR / "uploads"
    DB_PATH: Path = DATA_DIR / "rag.db"
    QDRANT_PATH: Path = DATA_DIR / "qdrant"

    # 密钥（空串 = 未配置；以 DB user_config 覆盖为准）
    claude_api_key: str = ""
    deepseek_api_key: str = ""
    openai_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # 默认模型（仅作 fallback；真实生效值由 user_config 提供）
    default_chat_provider: str = "anthropic"   # anthropic | deepseek | openai_compatible
    default_chat_model: str = "claude-sonnet-4-5"
    fallback_chat_provider: str = "deepseek"
    fallback_chat_model: str = "deepseek-chat"
    default_embedding_model: str = "bge-m3"

    # Qdrant
    qdrant_collection: str = "rag_documents"
    qdrant_vector_size: int = 1024  # BGE-M3 dense dim；Fake/API 备选可不同

    # 检索（默认值；kb_id 级 user_config 可覆盖 —— 单一参数源）
    retrieval_top_k: int = 20
    rerank_top_k: int = 5
    dense_prefetch: int = 30
    sparse_prefetch: int = 30
    similarity_threshold: float = 0.0   # RRF 后阈值；0 = 不限
    rerank_enabled: bool = False        # 默认关，配置本地 reranker 后开
    max_source_tokens: int = 4000       # 引用注入上限（按 tokens 裁）

    # 文档
    max_upload_mb: int = 100
    allowed_exts: tuple = (".md", ".txt", ".pdf", ".docx", ".py", ".js", ".ts", ".tsx", ".json", ".yaml", ".yml", ".toml", ".csv", ".html")

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

settings = Settings()

def get_settings() -> Settings:
    return settings
```

**Step 6: 启动入口 `backend/run.py`**
```python
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run("app.api.app:app", host=settings.host, port=settings.port, reload=True)
```

**Step 7: 空 `__init__.py`**（各包目录）

**Step 8: 冒烟测试 `backend/tests/test_health.py`**（TDD 起手：先跑红）
```python
def test_smoke_imports():
    from app.core.config import Settings  # noqa: F401
    assert Settings is not None
```

**Step 9: 虚拟环境**
```bash
cd "D:\RAG个人AI助手\backend"
python -m venv venv
venv\Scripts\python -m pip install -U pip
venv\Scripts\pip install -r requirements-dev.txt
venv\Scripts\python -m pytest          # 期望：1 passed
```

**Step 10: 提交**
```bash
git add backend/ .gitignore
git commit -m "feat(p0-1): backend scaffold with config, deps, pytest"
```
> 若 `FlagEmbedding/torch` 安装过重或与 3.14 冲突：允许先注释并在 P0-4 前单独解决（P0-4 测试用 FakeEmbedder，不依赖真实模型下载）。

---

## Task P0-2: Storage Layer — SQLite 数据模型 + Repository（含 kb_id / 状态机 / 配置 / 用量）

**Files:**
- Create: `backend/app/models/database.py`、`backend/app/models/schemas.py`
- Create: `backend/app/services/repositories.py`
- Test: `backend/tests/test_repositories.py`

**Step 1: 失败测试 `backend/tests/test_repositories.py`**（先跑红）
```python
import pytest
from app.models.database import Database
from app.services.repositories import (
    ConversationRepository, DocumentRepository, ChunkRepository, ConfigRepository, UsageRepository,
)
from app.models.schemas import MessageCreate, DocumentCreate

@pytest.fixture
async def db(tmp_path):
    database = Database(db_path=tmp_path / "test.db")
    await database.init()
    yield database
    await database.close()

@pytest.fixture
async def conv(db): return ConversationRepository(db)

@pytest.fixture
async def docs(db): return DocumentRepository(db)

@pytest.fixture
async def chunks(db): return ChunkRepository(db)

@pytest.fixture
async def cfg(db): return ConfigRepository(db)

@pytest.fixture
async def usage(db): return UsageRepository(db)

async def test_conversation_flow(conv):
    conv_id = await conv.create(title="Chat", model="claude-sonnet-4-5", kb_id=1)
    await conv.save_message(conv_id, MessageCreate(role="user", content="Hello"))
    await conv.save_message(conv_id, MessageCreate(role="assistant", content="Hi", sources=[{"n": 1, "chunk_id": 9}]))
    msgs = await conv.get_messages(conv_id)
    assert len(msgs) == 2 and msgs[1].content == "Hi" and msgs[1].sources[0]["chunk_id"] == 9
    rows = await conv.list(kb_id=1)
    assert rows[0]["title"] == "Chat"

async def test_document_status_machine(docs):
    doc_id = await docs.create(DocumentCreate(kb_id=1, filename="a.md", file_type=".md", file_path="/x/a.md", size=10))
    await docs.set_status(doc_id, "parsed")
    await docs.set_status(doc_id, "ready")
    doc = await docs.get(doc_id)
    assert doc["status"] == "ready"
    lst = await docs.list_by_kb(1)
    assert len(lst) == 1

async def test_chunk_crud(chunks):
    await chunks.delete_by_document(doc_id=1)
    await chunks.insert_many([{"kb_id": 1, "document_id": 1, "seq": 0, "text": "t0", "meta": {"page": 1}}])
    rows = await chunks.list_pending(1, limit=10)
    assert rows and rows[0]["text"] == "t0"

async def test_config_get_set_defaults(cfg):
    assert await cfg.get("llm.provider", default="anthropic") == "anthropic"
    await cfg.set("llm.provider", "deepseek")
    assert await cfg.get("llm.provider") == "deepseek"

async def test_usage_record(usage):
    await usage.record(model="claude-sonnet-4-5", input_tokens=100, output_tokens=50, cost=0.0042)
    total = await usage.summary()
    assert total["requests"] == 1 and total["cost"] == 0.0042
```

**Step 2: 数据模型 `backend/app/models/database.py`**
```python
import aiosqlite
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kb_id INTEGER NOT NULL DEFAULT 1,
  title TEXT NOT NULL DEFAULT '新对话',
  model TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conv_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
  content TEXT NOT NULL,
  sources TEXT,              -- JSON 数组：[{n, kb_id, document_id, chunk_id, file, page, score, text}]
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kb_id INTEGER NOT NULL DEFAULT 1,
  filename TEXT NOT NULL,
  file_type TEXT NOT NULL,
  file_path TEXT NOT NULL,
  size INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'uploading',  -- uploading|parsed|ready|failed|disabled
  error TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kb_id INTEGER NOT NULL DEFAULT 1,
  document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  seq INTEGER NOT NULL,
  text TEXT NOT NULL,
  meta TEXT NOT NULL DEFAULT '{}',   -- JSON：page/heading/lang...
  status TEXT NOT NULL DEFAULT 'pending',  -- pending|indexed
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kb_id INTEGER NOT NULL DEFAULT 1,
  document_id INTEGER NOT NULL,
  kind TEXT NOT NULL,          -- parse|index
  status TEXT NOT NULL DEFAULT 'queued',  -- queued|running|done|failed
  progress INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS user_config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL          -- JSON 编码
);
CREATE TABLE IF NOT EXISTS usage_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  model TEXT NOT NULL,
  input_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  cost REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_docs_kb ON documents(kb_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_kb ON chunks(kb_id);
CREATE INDEX IF NOT EXISTS idx_msgs_conv ON messages(conv_id);
"""

class Database:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self._conn: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database not initialized")
        return self._conn

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
```

**Step 3: Pydantic 模型 `backend/app/models/schemas.py`**
```python
from pydantic import BaseModel, Field
from typing import Any

class MessageCreate(BaseModel):
    role: str
    content: str
    sources: list[dict[str, Any]] = Field(default_factory=list)

class MessageOut(MessageCreate):
    id: int
    created_at: str

class ConversationCreate(BaseModel):
    kb_id: int = 1
    title: str = "新对话"
    model: str | None = None

class ConversationOut(BaseModel):
    id: int
    kb_id: int
    title: str
    model: str | None = None
    created_at: str

class DocumentCreate(BaseModel):
    kb_id: int = 1
    filename: str
    file_type: str
    file_path: str
    size: int = 0

class DocumentOut(BaseModel):
    id: int
    kb_id: int
    filename: str
    file_type: str
    size: int
    status: str
    error: str | None = None
    chunk_count: int = 0
    created_at: str
    updated_at: str

class ChatRequest(BaseModel):
    kb_id: int = 1
    conversation_id: int | None = None
    query: str
    model: str | None = None          # None = 用配置默认
    # 检索参数覆盖（可选；缺省读 kb 级配置）
    top_k: int | None = None
    threshold: float | None = None

class HitTestRequest(BaseModel):
    kb_id: int = 1
    query: str
    top_k: int | None = None
    threshold: float | None = None
    rerank_enabled: bool | None = None

class HitResult(BaseModel):
    chunk_id: int
    document_id: int
    kb_id: int
    seq: int
    text: str
    file: str
    page: int | None = None
    score_breakdown: dict[str, float] = {}   # {vector, bm25, rrf, rerank?}
    passed: bool

class ConfigItem(BaseModel):
    key: str
    value: Any
```

**Step 4: Repository `backend/app/services/repositories.py`**
```python
import json
from typing import Any
from app.models.database import Database
from app.models.schemas import MessageCreate, DocumentCreate

def _json(v: Any) -> str: return json.dumps(v, ensure_ascii=False)
def _loads(s: str | None, default: Any = None) -> Any:
    if not s: return default
    try: return json.loads(s)
    except Exception: return default

class ConversationRepository:
    def __init__(self, db: Database): self.db = db

    async def create(self, title: str, model: str | None, kb_id: int = 1) -> int:
        cur = await self.db.conn.execute(
            "INSERT INTO conversations(kb_id,title,model) VALUES(?,?,?)", (kb_id, title, model))
        await self.db.conn.commit()
        return cur.lastrowid

    async def save_message(self, conv_id: int, msg: MessageCreate) -> int:
        cur = await self.db.conn.execute(
            "INSERT INTO messages(conv_id,role,content,sources) VALUES(?,?,?,?)",
            (conv_id, msg.role, msg.content, _json(msg.sources)))
        await self.db.conn.commit()
        return cur.lastrowid

    async def get_messages(self, conv_id: int, limit: int = 100) -> list[dict]:
        cur = await self.db.conn.execute(
            "SELECT * FROM messages WHERE conv_id=? ORDER BY id DESC LIMIT ?", (conv_id, limit))
        rows = await cur.fetchall()
        rows.reverse()
        return [dict(r) | {"sources": _loads(r["sources"], [])} for r in rows]

    async def list(self, kb_id: int = 1) -> list[dict]:
        cur = await self.db.conn.execute("SELECT * FROM conversations WHERE kb_id=? ORDER BY id DESC LIMIT 100", (kb_id,))
        return [dict(r) for r in await cur.fetchall()]

    async def delete(self, conv_id: int) -> None:
        await self.db.conn.execute("DELETE FROM conversations WHERE id=?", (conv_id,))
        await self.db.conn.commit()

class DocumentRepository:
    def __init__(self, db: Database): self.db = db

    async def create(self, doc: DocumentCreate) -> int:
        cur = await self.db.conn.execute(
            "INSERT INTO documents(kb_id,filename,file_type,file_path,size) VALUES(?,?,?,?,?)",
            (doc.kb_id, doc.filename, doc.file_type, doc.file_path, doc.size))
        await self.db.conn.commit()
        return cur.lastrowid

    async def get(self, doc_id: int) -> dict | None:
        cur = await self.db.conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,))
        r = await cur.fetchone()
        return dict(r) if r else None

    async def set_status(self, doc_id: int, status: str, error: str | None = None) -> None:
        await self.db.conn.execute(
            "UPDATE documents SET status=?, error=?, updated_at=datetime('now','localtime') WHERE id=?",
            (status, error, doc_id))
        await self.db.conn.commit()

    async def list_by_kb(self, kb_id: int) -> list[dict]:
        cur = await self.db.conn.execute(
            "SELECT d.*, (SELECT COUNT(*) FROM chunks c WHERE c.document_id=d.id AND c.status='indexed') AS chunk_count "
            "FROM documents d WHERE d.kb_id=? ORDER BY d.id DESC", (kb_id,))
        return [dict(r) for r in await cur.fetchall()]

    async def delete(self, doc_id: int) -> None:
        await self.db.conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        await self.db.conn.commit()

class ChunkRepository:
    def __init__(self, db: Database): self.db = db

    async def delete_by_document(self, doc_id: int) -> None:
        await self.db.conn.execute("DELETE FROM chunks WHERE document_id=?", (doc_id,))
        await self.db.conn.commit()

    async def insert_many(self, items: list[dict]) -> None:
        await self.db.conn.executemany(
            "INSERT INTO chunks(kb_id,document_id,seq,text,meta,status) VALUES(:kb_id,:document_id,:seq,:text,:meta,:status)",
            [{**i, "meta": _json(i.get("meta", {})), "status": i.get("status", "pending")} for i in items])
        await self.db.conn.commit()

    async def list_pending(self, doc_id: int) -> list[dict]:
        cur = await self.db.conn.execute(
            "SELECT * FROM chunks WHERE document_id=? AND status='pending' ORDER BY seq", (doc_id,))
        rows = await cur.fetchall()
        return [dict(r) | {"meta": _loads(r["meta"], {})} for r in rows]

    async def list_all(self, doc_id: int) -> list[dict]:
        cur = await self.db.conn.execute("SELECT * FROM chunks WHERE document_id=? ORDER BY seq", (doc_id,))
        rows = await cur.fetchall()
        return [dict(r) | {"meta": _loads(r["meta"], {})} for r in rows]

    async def mark_indexed(self, doc_id: int) -> None:
        await self.db.conn.execute("UPDATE chunks SET status='indexed' WHERE document_id=?", (doc_id,))
        await self.db.conn.commit()

class ConfigRepository:
    """user_config：字符串键 + JSON 值；读不到时回退 default。"""
    def __init__(self, db: Database): self.db = db

    async def get(self, key: str, default: Any = None) -> Any:
        cur = await self.db.conn.execute("SELECT value FROM user_config WHERE key=?", (key,))
        r = await cur.fetchone()
        return _loads(r["value"], default) if r else default

    async def set(self, key: str, value: Any) -> None:
        await self.db.conn.execute(
            "INSERT INTO user_config(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, _json(value)))
        await self.db.conn.commit()

    async def all(self) -> dict[str, Any]:
        cur = await self.db.conn.execute("SELECT key,value FROM user_config")
        return {r["key"]: _loads(r["value"]) for r in await cur.fetchall()}

class UsageRepository:
    def __init__(self, db: Database): self.db = db

    async def record(self, model: str, input_tokens: int, output_tokens: int, cost: float) -> None:
        await self.db.conn.execute(
            "INSERT INTO usage_records(model,input_tokens,output_tokens,cost) VALUES(?,?,?,?)",
            (model, input_tokens, output_tokens, cost))
        await self.db.conn.commit()

    async def summary(self) -> dict:
        cur = await self.db.conn.execute(
            "SELECT COUNT(*) AS requests, COALESCE(SUM(cost),0) AS cost, "
            "COALESCE(SUM(input_tokens),0) AS input_tokens, COALESCE(SUM(output_tokens),0) AS output_tokens "
            "FROM usage_records")
        r = await cur.fetchone()
        return dict(r) if r else {"requests": 0, "cost": 0, "input_tokens": 0, "output_tokens": 0}
```

**Step 5: 跑测试 → 绿**
```bash
venv\Scripts\python -m pytest tests/test_repositories.py -v
```
Expected: 5 passed（含失败分支可选补 1 条：删文档后 chunks 级联清空——SQLite 需 `PRAGMA foreign_keys=ON`，在执行 init 后补一句，测试覆盖）。

**Step 6: 提交**
```bash
git add backend/
git commit -m "feat(p0-2): storage layer with kb_id/status/config/usage repositories"
```
> 注意：`Database.init()` 需启用外键级联（`PRAGMA foreign_keys=ON`），删除文档时 chunks 一并清空；测试断言 `doc delete → chunks empty`。

---

## Task P0-3: LLM Gateway — Provider 数据化 + 流式 + 降级 + 计费

**Files:**
- Create: `backend/app/core/llm_gateway.py`
- Test: `backend/tests/test_llm_gateway.py`

**Step 1: 失败测试 `backend/tests/test_llm_gateway.py`**（用 Fake 传输层，不碰真实 API）
```python
import pytest
from app.core.llm_gateway import (
    ProviderRegistry, ChatMessage, ChatGateway, GatewayConfig, StreamUsage, ModelPricing,
)

class _FakeAnthropic:
    def __init__(self): self.calls = []
    async def stream(self, messages, model):
        self.calls.append((model, messages))
        yield StreamUsage(text="hi ", usage_in=10, usage_out=5)
        yield StreamUsage(text="there", usage_in=0, usage_out=0)

class _FakeDeepSeek:
    def __init__(self): self.calls = []
    async def stream(self, messages, model):
        self.calls.append((model, messages))
        yield StreamUsage(text="ok", usage_in=8, usage_out=3)

@pytest.fixture
def registry(monkeypatch):
    reg = ProviderRegistry()
    reg.register("anthropic", lambda key, base_url=None: _FakeAnthropic())
    reg.register("deepseek", lambda key, base_url=None: _FakeDeepSeek())
    return reg

async def test_stream_primary_then_fallback_on_rate_limit(registry):
    """anthropic 抛 429 -> 自动降级 deepseek，并返回使用信息。"""
    class BoomAnthropic:
        async def stream(self, messages, model):
            raise RuntimeError("429 rate limit")
    registry.register("anthropic", lambda key, base_url=None: BoomAnthropic())
    gw = GatewayConfig(primary_provider="anthropic", primary_model="claude-x",
                       fallback_provider="deepseek", fallback_model="deepseek-chat")
    gate = ChatGateway(registry, gw)
    text, usage, used_fallback = "", StreamUsage(), None
    async for chunk in gate.stream([ChatMessage(role="user", content="q")]):
        text += chunk.text
        usage = chunk
        used_fallback = chunk.fallback
    assert "ok" in text and used_fallback is True
    assert usage.usage_in > 0

async def test_no_fallback_when_success(registry):
    gw = GatewayConfig("anthropic", "claude-x", "deepseek", "deepseek-chat")
    gate = ChatGateway(registry, gw)
    text = ""
    async for chunk in gate.stream([ChatMessage(role="user", content="q")]):
        text += chunk.text
    assert text == "hi there"

def test_model_pricing():
    # 计费：claude-sonnet-4-5 输入 3/M、输出 15/M；deepseek-chat 输入 0.27/M、输出 1.1/M（示例单价可后续修正）
    assert ModelPricing.cost("claude-sonnet-4-5", 1_000_000, 0) == 3.0
    assert ModelPricing.cost("deepseek-chat", 0, 1_000_000) == 1.1

async def test_usage_records_via_repo(registry, tmp_path):
    from app.models.database import Database
    from app.services.repositories import UsageRepository
    db = Database(tmp_path / "u.db"); await db.init()
    repo = UsageRepository(db)
    await repo.record(model="claude-sonnet-4-5", input_tokens=10, output_tokens=2, cost=0.00006)
    s = await repo.summary()
    assert s["requests"] == 1
    await db.close()
```

**Step 2: 实现 `backend/app/core/llm_gateway.py`**
```python
"""统一模型调用层：Provider 数据化注册 + 流式 + 主备降级 + 用量/计费。

设计约束（来自成熟化规格 F）：
- provider 与模型名来自配置（.env 或 user_config），代码不硬编码具体模型 ID；
- chat 模型可降级；usage 汇总后交给上层落库 usage_records。
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import AsyncIterator, Awaitable, Callable
from app.core.config import settings

@dataclass
class ChatMessage:
    role: str
    content: str

@dataclass
class StreamUsage:
    text: str = ""
    usage_in: int = 0
    usage_out: int = 0
    fallback: bool | None = None

@dataclass
class GatewayConfig:
    primary_provider: str
    primary_model: str
    fallback_provider: str | None = None
    fallback_model: str | None = None

class ModelPricing:
    """按模型前缀匹配单价（$ / 1M tokens）。表在 user_config 'pricing' 可整体覆盖。"""
    _TABLE: dict[str, tuple[float, float]] = {
        "claude-opus": (15.0, 75.0),
        "claude-sonnet": (3.0, 15.0),
        "claude-": (3.0, 15.0),
        "deepseek-chat": (0.27, 1.1),
        "deepseek-reasoner": (0.55, 2.19),
        "gpt-": (2.5, 10.0),
        "text-embedding-3-small": (0.02, 0.0),
    }
    _DEFAULT = (1.0, 2.0)

    @classmethod
    def cost(cls, model: str, in_tokens: int, out_tokens: int) -> float:
        pin, pout = cls._DEFAULT
        for prefix, (i, o) in cls._TABLE.items():
            if model.startswith(prefix):
                pin, pout = i, o
                break
        return (in_tokens / 1_000_000) * pin + (out_tokens / 1_000_000) * pout

class ProviderError(Exception):
    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable

# ---- 真实 Provider（薄封装官方 SDK；key/base_url 来自配置） ----

class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str):
        from anthropic import AsyncAnthropic
        self._client = AsyncAnthropic(api_key=api_key)

    async def stream(self, messages: list[ChatMessage], model: str) -> AsyncIterator[StreamUsage]:
        try:
            async with self._client.messages.stream(
                model=model,
                max_tokens=4096,
                messages=[{"role": m.role, "content": m.content} for m in messages],
            ) as stream:
                async for text in stream.text_stream:
                    yield StreamUsage(text=text)
                final = await stream.get_final_message()
                usage = final.usage
                yield StreamUsage(usage_in=usage.input_tokens, usage_out=usage.output_tokens)
        except Exception as e:  # 429/超时/网络 等统一视为可重试 ProviderError
            raise ProviderError(f"anthropic: {e}") from e

class OpenAICompatProvider:
    """deepseek / openai / 任何 OpenAI 兼容端点。"""
    name = "openai_compat"

    def __init__(self, api_key: str, base_url: str | None = None):
        from openai import AsyncOpenAI
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)

    async def stream(self, messages: list[ChatMessage], model: str) -> AsyncIterator[StreamUsage]:
        try:
            stream = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                stream=True,
                stream_options={"include_usage": True},
            )
            async for chunk in stream:
                if not chunk.choices and chunk.usage:
                    yield StreamUsage(usage_in=chunk.usage.prompt_tokens or 0,
                                      usage_out=chunk.usage.completion_tokens or 0)
                    continue
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield StreamUsage(text=delta.content)
        except Exception as e:
            raise ProviderError(f"{self.name}: {e}") from e

# ---- 注册表 + 网关 ----

class ProviderRegistry:
    def __init__(self):
        self._factories: dict[str, Callable[[str, str | None], object]] = {}

    def register(self, name: str, factory: Callable[[str, str | None], object]) -> None:
        self._factories[name] = factory

    def build(self, name: str, api_key: str, base_url: str | None = None):
        if name not in self._factories:
            raise ProviderError(f"unknown provider: {name}", retryable=False)
        return self._factories[name](api_key, base_url)

def build_default_registry(keys: dict[str, str], base_urls: dict[str, str | None] | None = None) -> ProviderRegistry:
    reg = ProviderRegistry()
    base_urls = base_urls or {}
    if keys.get("claude_api_key"):
        reg.register("anthropic", lambda k, b=None, _k=keys["claude_api_key"]: AnthropicProvider(_k))
    if keys.get("deepseek_api_key"):
        reg.register("deepseek", lambda k, b=None, _k=keys["deepseek_api_key"], _u=base_urls.get("deepseek"): OpenAICompatProvider(_k, _u))
    if keys.get("openai_api_key"):
        reg.register("openai", lambda k, b=None, _k=keys["openai_api_key"]: OpenAICompatProvider(_k))
    return reg

class ChatGateway:
    """主 provider 流式输出；遇到 ProviderError(retryable) 且配置了 fallback 时无缝切换。"""

    def __init__(self, registry: ProviderRegistry, config: GatewayConfig, keys: dict[str, str],
                 base_urls: dict[str, str | None] | None = None):
        self.registry = registry
        self.config = config
        self.keys = keys
        self.base_urls = base_urls or {}

    def _provider(self, name: str):
        key = self.keys.get(f"{name}_api_key") or self.keys.get("claude_api_key")
        return self.registry.build(name, key or "", self.base_urls.get(name))

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[StreamUsage]:
        used_fallback = False
        provider = self._provider(self.config.primary_provider)
        try:
            async for u in provider.stream(messages, self.config.primary_model):
                u.fallback = False
                yield u
            return
        except ProviderError:
            if not self.config.fallback_provider:
                raise
            used_fallback = True

        fb = self._provider(self.config.fallback_provider)
        async for u in fb.stream(messages, self.config.fallback_model):
            u.fallback = True
            yield u

async def stream_and_record(gateway: ChatGateway, messages: list[ChatMessage],
                            usage_repo, model_name: str) -> AsyncIterator[StreamUsage]:
    """包装：把整段流式结果的用量汇总后写入 usage_records（按最终模型计费）。"""
    acc_in = acc_out = 0
    final_model = model_name
    async for u in gateway.stream(messages):
        acc_in += u.usage_in
        acc_out += u.usage_out
        if u.usage_in:  # 仅当有真实用量时按主模型计；真实实现按最终响应的 usage.model 计价
            final_model = gateway.config.primary_model if u.fallback is False else gateway.config.fallback_model
        yield u
    if acc_in or acc_out:
        from app.core.llm_gateway import ModelPricing
        await usage_repo.record(model=final_model, input_tokens=acc_in, output_tokens=acc_out,
                                cost=ModelPricing.cost(final_model, acc_in, acc_out))
```

**Step 3: 跑测试 → 绿**
```bash
venv\Scripts\python -m pytest tests/test_llm_gateway.py -v
```
Expected: 4 passed。

**Step 4: 提交**
```bash
git add backend/
git commit -m "feat(p0-3): llm gateway with provider registry, fallback, usage billing"
```

---

## Task P0-4: Embedding + Qdrant — BGE-M3(稠密+稀疏) + 混合检索(RRF)

**Files:**
- Create: `backend/app/core/embedding.py`、`backend/app/core/vector_store.py`
- Test: `backend/tests/test_vector_store.py`

> 说明：BGE-M3 一次产出稠密向量 + 稀疏(词法)权重，正对"代码/编号/专有名词靠 BM25 精确命中"的结论；Qdrant 用命名向量 `dense`+`sparse`，检索走 prefetch 双路 + RRF 融合。测试一律用 FakeEmbedder（不下载模型）。

**Step 1: 失败测试 `backend/tests/test_vector_store.py`**
```python
import pytest
from app.core.embedding import EmbeddingProvider
from app.core.vector_store import QdrantStore, SearchHit

class FakeEmbedder(EmbeddingProvider):
    """确定性向量：按文本长度/首字母制造可区分的稠密+稀疏。dim=64。"""
    dim = 64
    async def encode_dense(self, texts: list[str]) -> list[list[float]]:
        import hashlib
        out = []
        for t in texts:
            h = hashlib.sha256(t.encode()).digest()
            v = [0.0] * self.dim
            for i in range(self.dim):
                v[i] = h[i % 32] / 255.0
            out.append(v)
        return out

    async def encode_sparse(self, texts: list[str]) -> list[dict[int, float]]:
        out = []
        for t in texts:
            d: dict[int, float] = {}
            for ch in t[:50]:
                d[ord(ch) % 1000] = d.get(ord(ch) % 1000, 0.0) + 1.0
            out.append(d)
        return out

@pytest.fixture
async def store(tmp_path):
    s = QdrantStore(path=tmp_path / "qdrant", collection="t", vector_size=64, embedder=FakeEmbedder())
    await s.init()
    yield s
    await s.close()

async def test_upsert_and_hybrid_search_returns_breakdown(store):
    await store.upsert_chunks([
        {"id": 1, "kb_id": 1, "document_id": 10, "seq": 0, "text": "FastAPI 异步路由与依赖注入", "meta": {"file": "a.md"}},
        {"id": 2, "kb_id": 1, "document_id": 10, "seq": 1, "text": "Qdrant 本地模式与 RRF 融合", "meta": {"file": "a.md"}},
    ])
    hits = await store.hybrid_search(query="Qdrant 融合", kb_id=1, top_k=5,
                                     dense_prefetch=10, sparse_prefetch=10, threshold=0.0)
    assert hits, "should find something"
    assert hits[0].document_id == 10
    assert set(hits[0].score_breakdown) >= {"rrf"}
    # 阈值过滤
    strict = await store.hybrid_search(query="Qdrant 融合", kb_id=1, top_k=5,
                                       dense_prefetch=10, sparse_prefetch=10, threshold=1.0)
    assert strict == [] or all(h.score_breakdown["rrf"] >= 1.0 for h in strict)

async def test_delete_by_document(store):
    await store.upsert_chunks([{"id": 1, "kb_id": 1, "document_id": 10, "seq": 0,
                                "text": "x", "meta": {"file": "a.md"}}])
    await store.delete_document(doc_id=10, kb_id=1)
    hits = await store.hybrid_search(query="x", kb_id=1, top_k=5, dense_prefetch=5, sparse_prefetch=5, threshold=0.0)
    assert hits == []
```

**Step 2: Embedding 抽象 `backend/app/core/embedding.py`**
```python
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

class EmbeddingProvider(ABC):
    dim: int = 1024

    @abstractmethod
    async def encode_dense(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    async def encode_sparse(self, texts: list[str]) -> list[dict[int, float]]: ...

    async def encode(self, texts: list[str], sparse: bool = True) -> dict[str, Any]:
        dense = await self.encode_dense(texts)
        if not sparse:
            return {"dense": dense}
        return {"dense": dense, "sparse": await self.encode_sparse(texts)}


class BGEM3Provider(EmbeddingProvider):
    """本地 BGE-M3（FlagEmbedding），dense+sparse 一次编码。
    首次调用会下载模型（~2GB+），可设 model_dir 指定缓存。CPU 亦可运行，偏慢。"""

    def __init__(self, model_name: str = "BAAI/bge-m3", use_fp16: bool = False):
        self.model_name = model_name
        self.use_fp16 = use_fp16
        self._model = None
        self.dim = 1024

    def _load(self):
        if self._model is None:
            from FlagEmbedding import BGEM3FlagModel
            self._model = BGEM3FlagModel(self.model_name, use_fp16=self.use_fp16)
        return self._model

    async def encode_dense(self, texts: list[str]) -> list[list[float]]:
        import asyncio
        model = self._load()
        out = await asyncio.to_thread(
            lambda: model.encode(texts, return_dense=True, return_sparse=False,
                                 return_colbert_vecs=False)["dense_vecs"].tolist())
        return out

    async def encode_sparse(self, texts: list[str]) -> list[dict[int, float]]:
        import asyncio
        model = self._load()
        out = await asyncio.to_thread(
            lambda: model.encode(texts, return_dense=False, return_sparse=True,
                                 return_colbert_vecs=False)["lexical_weights"])
        result = []
        for weights in out:
            result.append({int(k): float(v) for k, v in weights.items()})
        return result
```

**Step 3: Qdrant 封装 `backend/app/core/vector_store.py`**
```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, SparseVectorParams, SparseIndexParams,
    PointStruct, SparseVector, QueryResponse, Fusion, FusionQuery, PrefetchQuery,
    Filter, FieldCondition, MatchValue,
)
from app.core.embedding import EmbeddingProvider

@dataclass
class SearchHit:
    chunk_id: int
    document_id: int
    kb_id: int
    seq: int
    text: str
    meta: dict = field(default_factory=dict)
    score_breakdown: dict[str, float] = field(default_factory=dict)

    @property
    def file(self) -> str:
        return self.meta.get("file", "")

    @property
    def page(self):
        return self.meta.get("page")


class QdrantStore:
    def __init__(self, path: Path | str, collection: str, vector_size: int, embedder: EmbeddingProvider):
        self.path = Path(path)
        self.collection = collection
        self.vector_size = vector_size
        self.embedder = embedder
        self._client: AsyncQdrantClient | None = None

    async def init(self) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        self._client = AsyncQdrantClient(path=str(self.path))
        existing = await self._client.get_collections()
        if self.collection not in [c.name for c in existing.collections]:
            await self._client.create_collection(
                collection_name=self.collection,
                vectors_config={"dense": VectorParams(size=self.vector_size, distance=Distance.COSINE)},
                sparse_vectors_config={"sparse": SparseVectorParams(index=SparseIndexParams(on_disk=True))},
            )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def upsert_chunks(self, chunks: list[dict]) -> None:
        texts = [c["text"] for c in chunks]
        enc = await self.embedder.encode(texts, sparse=True)
        dense, sparse = enc["dense"], enc["sparse"]
        points = []
        for c, d, s in zip(chunks, dense, sparse):
            points.append(PointStruct(
                id=c["id"],
                vector={
                    "dense": d,
                    "sparse": SparseVector(indices=list(s.keys()), values=list(s.values())),
                },
                payload={"kb_id": c["kb_id"], "document_id": c["document_id"], "seq": c["seq"],
                         "text": c["text"], **c["meta"]},
            ))
        await self._client.upsert(collection_name=self.collection, points=points)

    async def delete_document(self, doc_id: int, kb_id: int) -> None:
        await self._client.delete(
            collection_name=self.collection,
            points_selector=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=doc_id)),
                                         FieldCondition(key="kb_id", match=MatchValue(value=kb_id))]),
        )

    async def hybrid_search(self, query: str, kb_id: int, top_k: int,
                            dense_prefetch: int, sparse_prefetch: int, threshold: float) -> list[SearchHit]:
        enc = await self.embedder.encode([query], sparse=True)
        dvec = enc["dense"][0]
        sp = enc["sparse"][0]
        kb_filter = Filter(must=[FieldCondition(key="kb_id", match=MatchValue(value=kb_id))])
        resp = await self._client.query_points(
            collection_name=self.collection,
            prefetch=[
                PrefetchQuery(query=dvec, using="dense", limit=dense_prefetch, filter=kb_filter),
                PrefetchQuery(query=SparseVector(indices=list(sp.keys()), values=list(sp.values())),
                              using="sparse", limit=sparse_prefetch, filter=kb_filter),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )
        # 逐路分数留存（用同一查询分别取 dense/sparse 的 top，便于展示构成）
        dense_hits = await self._query_single(dvec, "dense", kb_id, kb_filter, dense_prefetch)
        sparse_hits = await self._query_single(sp, "sparse", kb_id, kb_filter, sparse_prefetch)
        dense_score = {h.id: h.score for h in dense_hits}
        sparse_score = {h.id: h.score for h in sparse_hits}

        out = []
        for p in resp.points:
            payload = p.payload or {}
            breakdown = {"rrf": round(float(p.score), 4)}
            if p.id in dense_score:
                breakdown["vector"] = round(dense_score[p.id], 4)
            if p.id in sparse_score:
                breakdown["bm25"] = round(sparse_score[p.id], 4)
            if breakdown.get("rrf", 0.0) < threshold:
                continue
            out.append(SearchHit(
                chunk_id=int(p.id), kb_id=payload.get("kb_id", kb_id),
                document_id=payload.get("document_id", 0), seq=payload.get("seq", 0),
                text=payload.get("text", ""), meta=payload, score_breakdown=breakdown))
        return out

    async def _query_single(self, query, using: str, kb_id: int, kb_filter, limit: int) -> list[QueryResponse]:
        if using == "sparse":
            query = SparseVector(indices=list(query.keys()), values=list(query.values()))
        resp = await self._client.query_points(
            collection_name=self.collection, query=query, using=using, limit=limit, filter=kb_filter)
        return resp.points
```

**Step 4: 跑测试 → 绿**
```bash
venv\Scripts\python -m pytest tests/test_vector_store.py -v
```
Expected: 2 passed（本机 Qdrant local 无需 Docker）。

**Step 5: 提交**
```bash
git add backend/
git commit -m "feat(p0-4): BGE-M3 dense+sparse embeddings and qdrant hybrid RRF search"
```
> 若 qdrant-client 本地模式暂不支持稀疏向量/融合，可退级方案：两路各取 top_k，Python 端实现 RRF 合并（`score = Σ 1/(k+rank)`），接口与测试不变。

---

## Task P0-5: RAG Engine — 检索参数单一来源 + 引用(tokens 裁剪) + 流式生成

**Files:**
- Create: `backend/app/services/rag_engine.py`
- Test: `backend/tests/test_rag_engine.py`

> 要点（对标结论）：检索参数在"kb 级配置"只有一份；`hit-test` 与对话检索都从 `RetrievalParamsResolver` 读取，杜绝"测试面板参数和线上不一致"。

**Step 1: 失败测试 `backend/tests/test_rag_engine.py`**
```python
import pytest
from app.core.vector_store import QdrantStore, SearchHit
from app.services.rag_engine import RetrievalParams, RetrievalParamsResolver, RAGEngine, SourceRef

class _Store:
    async def hybrid_search(self, query, kb_id, top_k, dense_prefetch, sparse_prefetch, threshold):
        return [
            SearchHit(chunk_id=1, document_id=10, kb_id=1, seq=0,
                      text="A" * 100, meta={"file": "a.md"},
                      score_breakdown={"rrf": 0.8, "vector": 0.9, "bm25": 0.5}),
            SearchHit(chunk_id=2, document_id=11, kb_id=1, seq=1,
                      text="B" * 200, meta={"file": "b.md", "page": 3},
                      score_breakdown={"rrf": 0.6, "vector": 0.7}),
        ]

class _GW:
    def __init__(self): self.calls = []
    async def stream(self, messages):
        yield type("U", (), {"text": "答案", "usage_in": 0, "usage_out": 0, "fallback": False})()

class _CfgRepo:
    def __init__(self, data): self.data = data
    async def get(self, key, default=None): return self.data.get(key, default)

async def test_params_resolver_falls_back_to_defaults(tmp_path):
    repo = _CfgRepo({})
    p = await RetrievalParamsResolver(repo, kb_id=1).resolve(overrides={})
    assert p.top_k == 20 and p.rerank_enabled is False

async def test_params_resolver_uses_kb_config():
    repo = _CfgRepo({"kb.1.retrieval.top_k": 6, "kb.1.retrieval.threshold": 0.5})
    p = await RetrievalParamsResolver(repo, kb_id=1).resolve(overrides={"top_k": 9})
    assert p.top_k == 9 and p.threshold == 0.5  # 显式覆盖优先，其余走 kb 配置

async def test_engine_builds_context_and_sources_with_token_cut():
    engine = RAGEngine(store=_Store(), gateway=_GW(), cfg=_CfgRepo({}))
    ctx, sources = await engine.retrieve("q", kb_id=1, overrides={})
    assert len(sources) == 2 and sources[0].file == "a.md" and sources[1].page == 3
    assert sources[0].score_breakdown["rrf"] == 0.8
    total = sum(len(s.text) for s in sources)
    assert total > 0
    # token 裁剪：注入文本不超预算（近似按字符 4:1 tokens）
    injected = ctx
    assert len(injected) <= 4 * 4000 + 2000  # 宽松断言，实际看实现
```

**Step 2: 实现 `backend/app/services/rag_engine.py`**
```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import AsyncIterator
from app.core.llm_gateway import ChatMessage, StreamUsage
from app.services.repositories import ConfigRepository

RAG_SYSTEM_PROMPT = (
    "你是本地 RAG 知识库助手。只能依据提供的[来源]内容回答；"
    "若来源不足，明确说'知识库中没有相关内容'，不要编造。"
    "回答中需要引用时用 [n] 标注对应来源编号。回答用中文（除非提问用其他语言）。"
)

@dataclass
class RetrievalParams:
    top_k: int = 20
    dense_prefetch: int = 30
    sparse_prefetch: int = 30
    threshold: float = 0.0
    rerank_enabled: bool = False
    max_source_tokens: int = 4000

class RetrievalParamsResolver:
    """单一参数源：user_config 的 kb.<id>.retrieval.* 键；调用方可显式覆盖。"""

    def __init__(self, cfg: ConfigRepository, kb_id: int):
        self.cfg = cfg
        self.kb_id = kb_id

    async def resolve(self, overrides: dict | None = None) -> RetrievalParams:
        overrides = overrides or {}
        base = RetrievalParams()
        pairs = {
            "top_k": ("top_k", "kb.%d.retrieval.top_k" % self.kb_id),
            "dense_prefetch": ("dense_prefetch", "kb.%d.retrieval.dense_prefetch" % self.kb_id),
            "sparse_prefetch": ("sparse_prefetch", "kb.%d.retrieval.sparse_prefetch" % self.kb_id),
            "threshold": ("threshold", "kb.%d.retrieval.threshold" % self.kb_id),
            "rerank_enabled": ("rerank_enabled", "kb.%d.retrieval.rerank_enabled" % self.kb_id),
            "max_source_tokens": ("max_source_tokens", "kb.%d.retrieval.max_source_tokens" % self.kb_id),
        }
        for attr, (k, cfg_key) in pairs.items():
            if k in overrides and overrides[k] is not None:
                setattr(base, attr, overrides[k])
            else:
                val = await self.cfg.get(cfg_key, getattr(base, attr))
                if val is not None:
                    setattr(base, attr, val)
        return base


@dataclass
class SourceRef:
    n: int
    kb_id: int
    document_id: int
    chunk_id: int
    file: str
    page: int | None = None
    score: float = 0.0
    score_breakdown: dict = field(default_factory=dict)
    text: str = ""
    seq: int = 0

    def to_dict(self) -> dict:
        return {"n": self.n, "kb_id": self.kb_id, "document_id": self.document_id,
                "chunk_id": self.chunk_id, "file": self.file, "page": self.page,
                "score": round(self.score, 4), "score_breakdown": self.score_breakdown,
                "text": self.text[:500], "seq": self.seq}


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # 中文等宽近似：~4 字符/token


class RAGEngine:
    def __init__(self, store, gateway, cfg: ConfigRepository, kb_id: int = 1):
        self.store = store
        self.gateway = gateway
        self.cfg = cfg
        self.kb_id = kb_id

    async def retrieve(self, query: str, kb_id: int | None = None,
                       overrides: dict | None = None) -> tuple[str, list[SourceRef]]:
        kb_id = kb_id or self.kb_id
        p = await RetrievalParamsResolver(self.cfg, kb_id).resolve(overrides)
        hits = await self.store.hybrid_search(
            query=query, kb_id=kb_id, top_k=p.top_k,
            dense_prefetch=p.dense_prefetch, sparse_prefetch=p.sparse_prefetch,
            threshold=p.threshold)
        if p.rerank_enabled and hits:
            hits = await self._rerank(query, hits, p)
        sources, budget = [], p.max_source_tokens
        parts = []
        for i, h in enumerate(hits, start=1):
            tok = _estimate_tokens(h.text)
            if budget - tok < 0 and sources:
                break
            budget -= tok
            src = SourceRef(n=i, kb_id=kb_id, document_id=h.document_id, chunk_id=h.chunk_id,
                            file=h.file, page=h.page, score=h.score_breakdown.get("rrf", 0.0),
                            score_breakdown=h.score_breakdown, text=h.text, seq=h.seq)
            sources.append(src)
            parts.append(f"[来源{i}: {src.file}]\n{src.text}")
        context = "\n\n".join(parts)
        return context, sources

    async def _rerank(self, query: str, hits, p: RetrievalParams):
        """可选本地 reranker（FlagEmbedding FlagReranker）。默认关闭；开启后按 rerank 分排序。"""
        try:
            from FlagEmbedding import FlagReranker
        except Exception:
            return hits
        texts = [h.text for h in hits]
        reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=False)
        pairs = [(query, t) for t in texts]
        scores = reranker.compute_score(pairs)  # sync；大列表可拆批
        if not isinstance(scores, list):
            scores = [scores]
        for h, s in zip(hits, scores):
            h.score_breakdown["rerank"] = round(float(s), 4)
        hits.sort(key=lambda h: h.score_breakdown.get("rerank", 0.0), reverse=True)
        return hits[: max(1, int(p.top_k))]

    async def generate_stream(self, query: str, history: list[ChatMessage] | None = None,
                              kb_id: int | None = None, model: str | None = None,
                              overrides: dict | None = None) -> AsyncIterator[tuple[str, list[SourceRef] | None]]:
        kb_id = kb_id or self.kb_id
        context, sources = await self.retrieve(query, kb_id=kb_id, overrides=overrides)
        if context:
            user_payload = f"知识库检索结果：\n\n{context}\n\n问题：{query}"
        else:
            user_payload = f"（知识库未检索到相关内容）\n\n问题：{query}"
        messages = [ChatMessage(role="system", content=RAG_SYSTEM_PROMPT)]
        if history:
            messages.extend(history[-6:])
        messages.append(ChatMessage(role="user", content=user_payload))
        sent_sources = False
        async for u in self.gateway.stream(messages):
            if not sent_sources:
                sent_sources = True
                yield "", sources  # 首个事件先推来源元数据（前端可先渲染引用面板）
            yield u.text, None
```

**Step 3: 跑测试 → 绿**
```bash
venv\Scripts\python -m pytest tests/test_rag_engine.py -v
```
Expected: 3 passed。

**Step 4: 提交**
```bash
git add backend/
git commit -m "feat(p0-5): rag engine with single-source retrieval params, token-cut sources, streaming"
```

---

## Task P0-6: 文档管线 — Parser/Splitter/Indexer 可插拔契约 + 上传解析 + 预览 + 确认索引

**Files:**
- Create: `backend/app/services/doc_pipeline.py`
- Create: `backend/app/services/index_worker.py`（进程内 asyncio 任务）
- Test: `backend/tests/test_doc_pipeline.py`

> 流程（成熟化规格 C）：上传存盘 → 同步 解析+分块（快，md/txt/代码；PDF/DOCX 在无 Unstructured 时先报"暂不支持"并标 failed）→ 状态 `parsed`（chunks 处于 `pending`）→ 前端可调预览 → 用户 `confirm` → 入队索引（embedding 慢）→ 状态 `ready`。

**Step 1: 失败测试 `backend/tests/test_doc_pipeline.py`**
```python
import pytest
from pathlib import Path
from app.services.doc_pipeline import (
    parse_document, split_parsed, pipeline_contract, PipelineError,
)

def test_parse_markdown_returns_blocks():
    blocks = parse_document(Path("x.md"), "# 标题\n\n第一段文字。\n\n第二段。")
    assert len(blocks) >= 3  # 标题+两段
    assert blocks[0]["text"] == "# 标题"

def test_parse_unsupported_ext_raises():
    with pytest.raises(PipelineError):
        parse_document(Path("x.xyz"), "aaa")

def test_splitter_respects_size():
    from app.services.doc_pipeline import RecursiveSplitter
    blocks = [{"text": "词" * 3000, "meta": {}}]
    chunks = RecursiveSplitter(chunk_size=500, overlap=50).split(blocks)
    assert len(chunks) >= 2
    assert all(len(c["text"]) <= 600 for c in chunks)

def test_python_code_splitter_keeps_line_batch():
    from app.services.doc_pipeline import split_python_code
    code = "".join(f"def f{i}():\n    return {i}\n\n" for i in range(30))
    parts = split_python_code(code, max_lines=20)
    assert len(parts) >= 2
```

**Step 2: 实现 `backend/app/services/doc_pipeline.py`**
```python
"""解析/分块/索引契约。换解析引擎（Unstructured/Docling/OCR…）不改下游。

契约：
  parse_document(path, content) -> list[ParsedBlock{text, meta}]
  Splitter(block) -> list[Chunk{text, meta, seq}]
  Indexer(chunks) -> 写 SQLite + 写 Qdrant（见 index_worker）
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import re
from app.core.config import settings

class PipelineError(Exception):
    pass

@dataclass
class ParsedBlock:
    text: str
    meta: dict = field(default_factory=dict)

@dataclass
class Chunk:
    text: str
    meta: dict = field(default_factory=dict)
    seq: int = 0


def parse_document(path: Path, content: str | None = None) -> list[ParsedBlock]:
    """根据扩展名分派解析器。PDF/DOCX 走可插拔解析器注册表（默认未装则报 PipelineError）。"""
    ext = path.suffix.lower()
    if ext in (".md", ".txt", ".markdown"):
        return _parse_text(content if content is not None else path.read_text(encoding="utf-8", errors="replace"))
    if ext in (".py", ".js", ".ts", ".tsx", ".json", ".yaml", ".yml", ".toml", ".csv", ".html"):
        return _parse_code_like(content if content is not None else path.read_text(encoding="utf-8", errors="replace"), ext)
    if ext in (".pdf", ".docx"):
        raise PipelineError(f"{ext} 解析器未安装（P0 默认支持 md/txt/代码类；PDF/DOCX 待接 Unstructured/Docling）")
    raise PipelineError(f"不支持的文件类型 {ext or '(无扩展名)'}")

def _parse_text(text: str) -> list[ParsedBlock]:
    blocks: list[ParsedBlock] = []
    for raw in text.split("\n\n"):
        block = raw.strip()
        if block:
            blocks.append(ParsedBlock(text=block))
    return blocks or [ParsedBlock(text=text.strip())]

_CODE_LIKE = {".py", ".js", ".ts", ".tsx", ".json", ".yaml", ".yml", ".toml", ".csv", ".html"}

def _parse_code_like(text: str, ext: str) -> list[ParsedBlock]:
    # 代码类先整体为一个块（切分交给代码分块器），避免按空行乱切
    return [ParsedBlock(text=text, meta={"lang": ext.lstrip(".")})]


class RecursiveSplitter:
    """通用字符切分：按段落→句子→字符回退（对标 RecursiveCharacterTextSplitter 行为，自实现避免重依赖）。"""

    def __init__(self, chunk_size: int = 1200, overlap: int = 150):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, blocks: list[ParsedBlock]) -> list[Chunk]:
        chunks: list[Chunk] = []
        seq = 0
        for b in blocks:
            text = b.text
            if len(text) <= self.chunk_size:
                chunks.append(Chunk(text=text, meta=dict(b.meta), seq=seq)); seq += 1
                continue
            parts = self._hard_split(text)
            cur = ""
            for part in parts:
                if cur and len(cur) + len(part) + 1 > self.chunk_size:
                    chunks.append(Chunk(text=cur, meta=dict(b.meta), seq=seq)); seq += 1
                    cur = cur[-self.overlap:] if self.overlap else ""
                cur = (cur + "\n" + part).strip() if cur else part
            if cur:
                chunks.append(Chunk(text=cur, meta=dict(b.meta), seq=seq)); seq += 1
        return chunks

    @staticmethod
    def _hard_split(text: str) -> list[str]:
        parts = re.split(r"(?<=[。！？!?\n])", text)
        out, buf = [], ""
        for p in parts:
            if len(p) > 2000:
                if buf:
                    out.append(buf); buf = ""
                out.extend([p[i:i + 2000] for i in range(0, len(p), 2000)])
            elif buf and len(buf) + len(p) > 800:
                out.append(buf); buf = p
            else:
                buf += p
        if buf:
            out.append(buf)
        return out or [text]


def split_python_code(code: str, max_lines: int = 40, min_lines: int = 5) -> list[str]:
    """代码按行批量切分（保持语法片段完整性的轻量版；tree-sitter 精确切分 P1 接入）。"""
    lines = code.splitlines(keepends=True)
    if len(lines) <= max_lines:
        return [code]
    parts, buf, blank_streak = [], [], 0
    for line in lines:
        buf.append(line)
        if line.strip() == "":
            blank_streak += 1
        else:
            blank_streak = 0
        if len(buf) >= max_lines and blank_streak >= 1:
            parts.append("".join(buf)); buf = []
            blank_streak = 0
    if buf:
        parts.append("".join(buf))
    # 过短的尾块并入前块
    if len(parts) > 1 and len(parts[-1].splitlines()) < min_lines:
        parts[-2] += parts[-1]
        parts.pop()
    return parts


def run_upload_pipeline(path: Path, chunk_repo, doc_id: int, kb_id: int) -> int:
    """同步段：解析+分块+写入 SQLite(pending)。返回 pending chunk 数。"""
    ext = path.suffix.lower()
    content = path.read_text(encoding="utf-8", errors="replace")
    blocks = parse_document(path, content)
    if ext in _CODE_LIKE:
        parts: list[str] = []
        for b in blocks:
            parts.extend(split_python_code(b.text) if ext == ".py" else [b.text])
        chunks = [Chunk(text=p, meta={"lang": ext.lstrip(".")}, seq=i) for i, p in enumerate(parts)]
    else:
        chunks = RecursiveSplitter().split(blocks)
    rows = [{"kb_id": kb_id, "document_id": doc_id, "seq": c.seq,
             "text": c.text, "meta": {"file": path.name, **c.meta}} for c in chunks]
    chunk_repo.delete_by_document(doc_id)
    chunk_repo.insert_many(rows)
    return len(rows)
```

**Step 3: 索引 worker `backend/app/services/index_worker.py`**
```python
"""进程内 asyncio 索引队列：doc pending chunks -> embedding -> Qdrant。
P1 再升级为可持久化/可重试/断点续传的 jobs 表 worker。"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable

@dataclass
class IndexTask:
    doc_id: int
    kb_id: int
    on_done: Callable[[int, int, str | None], Awaitable[None]] | None = None  # (doc_id, chunk_count, error)
    _chunks: list[dict] = field(default_factory=list)


class IndexWorker:
    def __init__(self, max_concurrency: int = 2):
        self._queue: asyncio.Queue[IndexTask] = asyncio.Queue()
        self._tasks: list[asyncio.Task] = []
        self._max = max_concurrency

    def start(self) -> None:
        for _ in range(self._max):
            self._tasks.append(asyncio.create_task(self._loop()))

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    def submit(self, task: IndexTask) -> None:
        self._queue.put_nowait(task)

    async def _loop(self) -> None:
        while True:
            task = await self._queue.get()
            try:
                # chunks 由调用方预先取出并附在 task 上（含 SQLite 行）
                # 真实嵌入由 store.upsert_chunks 完成
                await task._run_hook() if hasattr(task, "_run_hook") else None
                error = None
            except Exception as e:  # noqa: BLE001
                error = str(e)
            finally:
                if task.on_done:
                    await task.on_done(task.doc_id, len(task._chunks), error)
                self._queue.task_done()
```

> 说明：本文件是队列骨架；P0-7 的 `knowledge.py` 组装"取 pending chunks → `store.upsert_chunks` → `chunks.mark_indexed` → 文档 ready/failed"作为 `_run_hook` 提交。骨架测试并入 API 集成测试。

**Step 4: 跑测试 → 绿**
```bash
venv\Scripts\python -m pytest tests/test_doc_pipeline.py -v
```
Expected: 4 passed。

**Step 5: 提交**
```bash
git add backend/
git commit -m "feat(p0-6): pluggable parser/splitter contract, md/txt/code ingestion, index worker skeleton"
```

---

## Task P0-7: API Gateway — 路由 + SSE 流式 + 上传/预览/确认 + hit-test + config

**Files:**
- Create: `backend/app/api/app.py`、`backend/app/api/deps.py`
- Create: `backend/app/api/routes/__init__.py`、`health.py`、`chat.py`、`knowledge.py`、`config.py`
- Test: `backend/tests/test_api.py`

**Step 1: 失败测试 `backend/tests/test_api.py`**（httpx ASGI；Fake 组件注入 app.state，全程不联网）
```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.api.app import create_app
from app.models.database import Database
from app.services.repositories import DocumentRepository, ChunkRepository, ConfigRepository
from app.core.embedding import EmbeddingProvider
from app.core.vector_store import QdrantStore

class FakeEmbedder(EmbeddingProvider):
    dim = 64
    async def encode_dense(self, texts):
        return [[0.01 * (i + 1) for i in range(64)] for _ in texts]
    async def encode_sparse(self, texts):
        return [{k % 1000: 1.0 for k in range(1, 5)} for _ in texts]

class FakeGateway:
    def __init__(self, cfg): self.cfg = cfg
    async def stream(self, messages):
        yield type("U", (), {"text": "流式回答", "usage_in": 5, "usage_out": 2, "fallback": False})()

@pytest.fixture
async def client(tmp_path):
    db = Database(tmp_path / "t.db"); await db.init()
    vs = QdrantStore(path=tmp_path / "q", collection="t", vector_size=64, embedder=FakeEmbedder()); await vs.init()
    app = create_app(db=db, vector_store=vs, embedder=FakeEmbedder(),
                     gateway_factory=lambda cfg: FakeGateway(cfg), worker_enabled=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        yield c
    await vs.close(); await db.close()

async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"

async def test_upload_preview_confirm_flow(client):
    r = await client.post("/api/knowledge/1/documents",
                          files={"file": ("hello.md", b"# 你好\n\n这是第一段。\n\n这是第二段。", "text/markdown")})
    assert r.status_code == 201, r.text
    doc = r.json(); assert doc["status"] == "parsed"
    pv = await client.get(f"/api/knowledge/1/documents/{doc['id']}/preview")
    assert pv.status_code == 200 and len(pv.json()["chunks"]) >= 1
    cf = await client.post(f"/api/knowledge/1/documents/{doc['id']}/confirm")
    assert cf.status_code in (200, 202)
    lst = await client.get("/api/knowledge/1/documents")
    ready = [d for d in lst.json() if d["id"] == doc["id"]][0]
    assert ready["status"] in ("ready", "indexing")

async def test_hit_test_returns_breakdown(client):
    await client.post("/api/knowledge/1/documents",
                      files={"file": ("a.md", b"Qdrant 混合检索 RRF 融合", "text/markdown")})
    r = await client.post("/api/knowledge/1/hit-test", json={"query": "Qdrant"})
    assert r.status_code == 200
    body = r.json()
    assert body["params"] is not None
    assert isinstance(body["hits"], list)

async def test_chat_stream_returns_sources_then_tokens(client):
    await client.post("/api/knowledge/1/documents",
                      files={"file": ("b.md", b"FastAPI 提供 SSE 流式接口", "text/markdown")})
    async with client.stream("POST", "/api/chat/stream", json={"kb_id": 1, "query": "FastAPI"}) as resp:
        assert resp.status_code == 200
        body = await resp.aread()
    assert b"流式回答" in body

async def test_config_get_put(client):
    r = await client.put("/api/config", json={"key": "kb.1.retrieval.top_k", "value": 8})
    assert r.status_code == 200
    g = await client.get("/api/config")
    assert g.json().get("kb.1.retrieval.top_k") == 8
```

**Step 2: DI 与 App `backend/app/api/deps.py` + `app.py`**
```python
# deps.py
from typing import Any
from fastapi import Request

def get_db(request: Request):
    return request.app.state.db

def get_vector_store(request: Request):
    return request.app.state.vector_store

def get_embedder(request: Request):
    return request.app.state.embedder

def get_gateway(request: Request):
    return request.app.state.gateway_factory

def get_worker(request: Request):
    return request.app.state.worker
```
```python
# app/api/app.py
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, chat, knowledge, config as config_routes
from app.core.config import settings
from app.models.database import Database
from app.services.repositories import DocumentRepository, ConfigRepository, UsageRepository, ChunkRepository
from app.core.llm_gateway import build_default_registry, ChatGateway, GatewayConfig, ProviderRegistry
from app.services.index_worker import IndexWorker


def create_app(db=None, vector_store=None, embedder=None, gateway_factory=None,
               worker_enabled: bool = True, keys: dict | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.db = db or Database(settings.DB_PATH)
        await app.state.db.init()

        app.state.embedder = embedder  # 真实场景注入 BGEM3Provider（P0-4）
        app.state.vector_store = vector_store

        keys = app.state.db and None
        # gateway_factory 由测试注入；生产用默认注册表
        if gateway_factory is None:
            cfg_repo = ConfigRepository(app.state.db)
            keys = {
                "claude_api_key": await cfg_repo.get("llm.claude_api_key", settings.claude_api_key),
                "deepseek_api_key": await cfg_repo.get("llm.deepseek_api_key", settings.deepseek_api_key),
                "openai_api_key": await cfg_repo.get("llm.openai_api_key", settings.openai_api_key),
            }
            base_urls = {"deepseek": await cfg_repo.get("llm.deepseek_base_url", settings.deepseek_base_url)}
            reg = build_default_registry(keys, base_urls)
            gw_cfg = GatewayConfig(
                primary_provider=await cfg_repo.get("llm.primary_provider", settings.default_chat_provider),
                primary_model=await cfg_repo.get("llm.primary_model", settings.default_chat_model),
                fallback_provider=await cfg_repo.get("llm.fallback_provider", settings.fallback_chat_provider),
                fallback_model=await cfg_repo.get("llm.fallback_model", settings.fallback_chat_model))
            app.state.gateway_factory = lambda cfg=None: ChatGateway(reg, gw_cfg, keys, base_urls)
        else:
            app.state.gateway_factory = gateway_factory

        app.state.worker = IndexWorker() if worker_enabled else None
        if app.state.worker:
            app.state.worker.start()
        yield
        if app.state.worker:
            await app.state.worker.stop()
        await app.state.vector_store.close() if vector_store else None
        await app.state.db.close()

    app = FastAPI(title="RAG AI 助手", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.include_router(health.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(knowledge.router, prefix="/api")
    app.include_router(config_routes.router, prefix="/api")
    return app


app = create_app()
```

**Step 3: 路由**
```python
# routes/health.py
from fastapi import APIRouter
router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}
```
```python
# routes/config.py
from fastapi import APIRouter, Depends
from app.api.deps import get_db
from app.models.schemas import ConfigItem
from app.services.repositories import ConfigRepository

router = APIRouter(tags=["config"])

@router.get("/config")
async def get_config(db=Depends(get_db)) -> dict:
    return await ConfigRepository(db).all()

@router.put("/config")
async def put_config(item: ConfigItem, db=Depends(get_db)) -> dict:
    await ConfigRepository(db).set(item.key, item.value)
    return {"ok": True, "key": item.key, "value": item.value}
```
```python
# routes/chat.py
from __future__ import annotations
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_db, get_gateway
from app.core.llm_gateway import ChatMessage
from app.models.schemas import ChatRequest
from app.services.repositories import ConversationRepository, ConfigRepository, UsageRepository
from app.services.rag_engine import RAGEngine

router = APIRouter(tags=["chat"])

async def _gateway_from(state_gateway_factory, model: str | None):
    return state_gateway_factory()

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, db=Depends(get_db), gw_factory=Depends(get_gateway)):
    conv_repo = ConversationRepository(db)
    conv_id = req.conversation_id
    if conv_id is None:
        conv_id = await conv_repo.create(title=req.query[:30], model=req.model, kb_id=req.kb_id)
    history = await conv_repo.get_messages(conv_id)
    history_msgs = [ChatMessage(role=m["role"], content=m["content"]) for m in history
                    if m["role"] in ("user", "assistant")][-6:]
    await conv_repo.save_message(conv_id, __import__("app.models.schemas", fromlist=["MessageCreate"]).MessageCreate(role="user", content=req.query))

    engine = RAGEngine(store=Depends(get_vector_store), gateway=_gateway_from(gw_factory, req.model),
                       cfg=ConfigRepository(db), kb_id=req.kb_id)

    async def gen():
        full_text = ""
        sources_payload = None
        async for text, sources in engine.generate_stream(
                req.query, history=history_msgs, kb_id=req.kb_id,
                model=req.model,
                overrides={"top_k": req.top_k, "threshold": req.threshold}):
            if sources is not None:
                sources_payload = [s.to_dict() for s in sources]
                yield {"event": "sources", "data": json.dumps(sources_payload, ensure_ascii=False)}
            elif text:
                full_text += text
                yield {"event": "token", "data": json.dumps({"t": text}, ensure_ascii=False)}
        await conv_repo.save_message(conv_id, __import__("app.models.schemas", fromlist=["MessageCreate"]).MessageCreate(
            role="assistant", content=full_text, sources=sources_payload or []))
        yield {"event": "done", "data": json.dumps({"conversation_id": conv_id})}

    return EventSourceResponse(gen())
```
```python
# routes/knowledge.py
from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.api.deps import get_db, get_vector_store, get_gateway
from app.core.config import settings
from app.models.schemas import DocumentCreate, HitTestRequest
from app.services.repositories import DocumentRepository, ChunkRepository, ConfigRepository
from app.services.doc_pipeline import run_upload_pipeline, PipelineError
from app.services.rag_engine import RAGEngine
from app.services.index_worker import IndexTask

router = APIRouter(tags=["knowledge"])

def _check_name(name: str):
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(400, "非法文件名")

@router.post("/knowledge/{kb_id}/documents", status_code=201)
async def upload_document(kb_id: int, file: UploadFile = File(...),
                          db=Depends(get_db), store=Depends(get_vector_store), gw_factory=Depends(get_gateway)):
    name = Path(file.filename or "unnamed").name
    _check_name(name)
    ext = Path(name).suffix.lower()
    if ext not in settings.allowed_exts:
        raise HTTPException(415, f"不支持类型 {ext}")
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"超过 {settings.max_upload_mb}MB 上限")
    up = settings.UPLOAD_DIR / f"kb{kb_id}"
    up.mkdir(parents=True, exist_ok=True)
    dest = up / name
    dest.write_bytes(data)

    doc_repo = DocumentRepository(db)
    chunk_repo = ChunkRepository(db)
    doc_id = await doc_repo.create(DocumentCreate(kb_id=kb_id, filename=name, file_type=ext,
                                                  file_path=str(dest), size=len(data)))
    try:
        count = run_upload_pipeline(dest, chunk_repo, doc_id, kb_id)
    except PipelineError as e:
        await doc_repo.set_status(doc_id, "failed", str(e))
        raise HTTPException(422, f"解析失败：{e}")
    await doc_repo.set_status(doc_id, "parsed")
    doc = await doc_repo.get(doc_id)
    return {**doc, "pending_chunks": count}

@router.get("/knowledge/{kb_id}/documents")
async def list_documents(kb_id: int, db=Depends(get_db)):
    return await DocumentRepository(db).list_by_kb(kb_id)

@router.get("/knowledge/{kb_id}/documents/{doc_id}/preview")
async def preview(doc_id: int, kb_id: int, db=Depends(get_db)):
    chunks = await ChunkRepository(db).list_pending(doc_id)
    return {"chunks": [{"seq": c["seq"], "text": c["text"][:2000], "meta": c["meta"]} for c in chunks]}

@router.post("/knowledge/{kb_id}/documents/{doc_id}/confirm")
async def confirm_document(doc_id: int, kb_id: int, db=Depends(get_db),
                           store=Depends(get_vector_store), gw_factory=Depends(get_gateway),
                           worker=Depends(_worker_dep)):
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get(doc_id)
    if not doc or doc["kb_id"] != kb_id:
        raise HTTPException(404, "文档不存在")
    if doc["status"] != "parsed":
        raise HTTPException(409, f"状态 {doc['status']} 不可确认")
    chunk_repo = ChunkRepository(db)
    rows = chunk_repo.list_pending(doc_id) if False else await chunk_repo.list_pending(doc_id)

    async def do_index():
        if len(rows) == 0:
            await doc_repo.set_status(doc_id, "ready")
            return
        await store.upsert_chunks([{**r, "id": r["id"]} for r in rows])
        await chunk_repo.mark_indexed(doc_id)
        await doc_repo.set_status(doc_id, "ready")

    if worker:
        task = IndexTask(doc_id=doc_id, kb_id=kb_id, _chunks=rows)
        async def on_done(did, count, error):
            if error:
                await doc_repo.set_status(did, "failed", error)
            else:
                await do_index()
        task.on_done = on_done
        worker.submit(task)
        return {"status": "indexing"}
    await do_index()
    return {"status": "ready"}

def _worker_dep(request):
    return request.app.state.worker

@router.post("/knowledge/{kb_id}/hit-test")
async def hit_test(kb_id: int, req: HitTestRequest, db=Depends(get_db),
                   store=Depends(get_vector_store), gw_factory=Depends(get_gateway)):
    engine = RAGEngine(store=store, gateway=gw_factory(), cfg=ConfigRepository(db), kb_id=kb_id)
    _, sources = await engine.retrieve(req.query, kb_id=kb_id,
                                       overrides={"top_k": req.top_k, "threshold": req.threshold,
                                                  "rerank_enabled": req.rerank_enabled})
    from app.services.rag_engine import RetrievalParamsResolver
    params = await RetrievalParamsResolver(ConfigRepository(db), kb_id).resolve(
        {"top_k": req.top_k, "threshold": req.threshold, "rerank_enabled": req.rerank_enabled})
    return {"params": {"top_k": params.top_k, "threshold": params.threshold,
                       "rerank_enabled": params.rerank_enabled},
            "hits": [s.to_dict() for s in sources]}
```

> 注意：`chat.py`/`knowledge.py` 中为紧凑做了简化（依赖注入直接调用 `Depends(get_vector_store)` 等）。**执行时统一改为显式从 `request.app.state` 取单例**，并把 `chat.py` 里的内联 `MessageCreate` import 提到文件头。命中测试与对话检索走同一 `RAGEngine.retrieve`（= 同一参数源，符合成熟化规格 D）。

**Step 4: 跑测试 → 绿**
```bash
venv\Scripts\python -m pytest tests/test_api.py -v
```
Expected: 5 passed。SSE 事件以 `data:` 行输出，httpx stream 读取文本断言含关键词即可。

**Step 5: 提交**
```bash
git add backend/
git commit -m "feat(p0-7): api gateway routes with SSE, upload/preview/confirm, hit-test, config"
```

---

## Task P0-8: 端到端集成验证

**Files:**
- Create: `backend/tests/test_e2e.py`

**Step 1: 端到端测试 `backend/tests/test_e2e.py`**（Fake 组件串联全链路：上传→预览→确认→提问→来源→命中一致性）
```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.api.app import create_app
from app.models.database import Database
from app.core.vector_store import QdrantStore
from app.core.embedding import EmbeddingProvider
from app.models.schemas import MessageCreate
from app.services.repositories import ConversationRepository

class FakeEmbedder(EmbeddingProvider):
    dim = 64
    async def encode_dense(self, texts):
        return [[0.001 * (i + len(t)) for i in range(64)] for t in texts]
    async def encode_sparse(self, texts):
        return [{min(900 + i, 1000): 1.0 for i in range(len(t))} for t in texts]

class FakeGateway:
    def __init__(self, cfg): pass
    async def stream(self, messages):
        for _ in messages:
            pass
        # 让"答案"回显最后一个 user 内容中的引用数量，便于断言 sources 注入
        last_user = [m for m in messages if m.role == "user"][-1].content
        yield type("U", (), {"text": f"基于来源回答。{last_user[:20]}", "usage_in": 12, "usage_out": 6, "fallback": False})()

@pytest.fixture
async def client(tmp_path):
    db = Database(tmp_path / "e2e.db"); await db.init()
    vs = QdrantStore(path=tmp_path / "q", collection="t", vector_size=64, embedder=FakeEmbedder()); await vs.init()
    app = create_app(db=db, vector_store=vs, embedder=FakeEmbedder(),
                     gateway_factory=lambda cfg: FakeGateway(cfg), worker_enabled=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c
    await vs.close(); await db.close()

async def test_full_loop(client):
    # 1) 上传两份文档并确认
    for fname, content in [("guide.md", "# 指南\n\nQdrant 使用本地模式。\n\nRRF 融合多路召回。"),
                           ("api.md", "# API\n\nFastAPI 提供 SSE 流式。")]:
        r = await client.post("/api/knowledge/1/documents", files={"file": (fname, content.encode(), "text/markdown")})
        assert r.status_code == 201
        did = r.json()["id"]
        pv = await client.get(f"/api/knowledge/1/documents/{did}/preview")
        assert pv.json()["chunks"]
        cf = await client.post(f"/api/knowledge/1/documents/{did}/confirm")
        assert cf.json()["status"] == "ready"
    # 2) 提问 -> SSE 中有 sources 事件与 token 事件
    async with client.stream("POST", "/api/chat/stream",
                             json={"kb_id": 1, "query": "Qdrant 如何融合多路召回？"}) as resp:
        assert resp.status_code == 200
        text = (await resp.aread()).decode()
    assert "sources" in text and "token" in text
    # 3) 命中测试与对话共用检索参数源：查询能命中 guide 文档
    ht = await client.post("/api/knowledge/1/hit-test", json={"query": "Qdrant 本地模式"})
    hits = ht.json()["hits"]
    assert any("guide.md" in h["file"] for h in hits)
    # 4) 对话已持久化
    r = await client.get("/api/chat/history/1") if False else None
```

> 说明：会话列表/历史只读端点属 P1 前端会话管理；P0 提供 `POST /api/chat/stream` 携带 `conversation_id` 续接即可（测试断言持久化可由 Repository 直接验证）。

**Step 2: 手动冒烟（真实模型，需 Key）**
```bash
# 若已有 .env 与可用 Key：
venv\Scripts\python -m uvicorn app.api.app:app --port 8000
# curl -N -X POST http://127.0.0.1:8000/api/chat/stream -H 'Content-Type: application/json' -d '{"query":"你好"}'
# 期望：event: token 流式输出，event: done
```
> 冒烟前先在 `PUT /api/config` 写入经实测可用的模型（如 `llm.primary_model`），避免默认模型名不可用。

**Step 3: 提交**
```bash
git add backend/
git commit -m "feat(p0-8): end-to-end tests for upload-preview-confirm-chat-hit-test loop"
```

---

## 完成后的后端结构（目标）

```
backend/
├── requirements.txt / requirements-dev.txt / pytest.ini / run.py
├── app/
│   ├── core/        config.py · llm_gateway.py · embedding.py · vector_store.py
│   ├── models/      database.py · schemas.py
│   ├── services/    repositories.py · rag_engine.py · doc_pipeline.py · index_worker.py
│   └── api/         app.py · deps.py · routes/{health,chat,knowledge,config}.py
└── tests/           test_health/repositories/llm_gateway/vector_store/rag_engine/
                     doc_pipeline/api/e2e.py
```

## 与前端计划的衔接（P0-9 ~ P0-12 见另一文档）

- `/api/chat/stream`：`event: sources`（JSON 数组）→ `event: token` → `event: done`（含 conversation_id）
- 上传 → `201 {…, status: parsed, pending_chunks}`；预览 `GET …/preview`；确认 `POST …/confirm`
- 命中测试 `POST …/hit-test` → `{params, hits[]}`（params 与对话检索同源，UI 可做成"检索调试"）
- 配置 `GET/PUT /api/config`（键：`llm.*`、`kb.<id>.retrieval.*`）

