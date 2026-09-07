# RAG AI 助手 — Phase 1: 后端骨架 + RAG 管线 实施计划

> **For Claude:** Use `${SUPERPOWERS_SKILLS_ROOT}/skills/collaboration/executing-plans/SKILL.md` to implement this plan task-by-task.

**Goal:** 搭建可运行的后端骨架，实现"上传文档 → 提问 → 基于 RAG 流式回答"的完整最小闭环。

**Architecture:** 分层架构，Storage → LLM Gateway → RAG Engine → API Gateway。每层通过接口通信，同层模块不耦合。Repository 模式抽象数据访问，Provider 模式抽象 LLM 调用。

**Tech Stack:** Python 3.12+ · FastAPI · LangChain · Qdrant (local) · SQLite · BGE-M3 · Claude/DeepSeek API

---

## 前置条件

- Python 3.12+ 已安装
- Node.js 18+ 已安装（前端后续用）
- 至少一个 LLM API Key（Claude 或 DeepSeek）
- Windows 环境，项目路径 `D:\rag`

---

### Task 1: 项目脚手架

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/run.py`

**Step 1: 创建目录结构**

```bash
cd D:\rag
mkdir -p backend/app/core backend/app/api backend/app/models backend/app/services backend/tests
```

**Step 2: 创建 requirements.txt**

```txt
# Web
fastapi==0.115.0
uvicorn[standard]==0.30.0
sse-starlette==2.1.0
python-multipart==0.0.9

# RAG
langchain==0.3.0
langchain-community==0.3.0
langchain-anthropic==0.3.0
langchain-openai==0.2.0
qdrant-client==1.11.0

# Embedding
sentence-transformers==3.0.0

# Document parsing
unstructured[md,pdf,docx]==0.15.0
tree-sitter==0.22.0

# Storage
aiosqlite==0.20.0

# Utils
python-dotenv==1.0.1
pydantic==2.9.0
pydantic-settings==2.5.0
```

**Step 3: 创建配置模块 `backend/app/core/config.py`**

```python
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """应用配置，从 .env 文件或环境变量读取"""

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = DATA_DIR / "uploads"
    DB_PATH: Path = DATA_DIR / "rag.db"
    QDRANT_PATH: Path = DATA_DIR / "qdrant"

    # LLM API Keys
    claude_api_key: str = ""
    deepseek_api_key: str = ""
    openai_api_key: str = ""

    # Default models
    default_chat_model: str = "claude-opus-4-8"
    fallback_chat_model: str = "deepseek-chat"
    default_embedding_model: str = "bge-m3"

    # Qdrant
    qdrant_collection: str = "rag_documents"
    qdrant_vector_size: int = 1024  # BGE-M3 output dim

    # RAG
    retrieval_top_k: int = 20
    rerank_top_k: int = 5
    hybrid_search_alpha: float = 0.7  # dense weight

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()
```

**Step 4: 创建启动入口 `backend/run.py`**

```python
import uvicorn
from app.core.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "app.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
```

**Step 5: 创建空 `__init__.py` 文件**

每个 `backend/app/` 子目录下放空的 `__init__.py`。

**Step 6: 创建虚拟环境并安装依赖**

```bash
cd D:\rag\backend
python -m venv venv
# Windows 激活: venv\Scripts\activate
venv\Scripts\pip install -r requirements.txt
```

**Step 7: 提交**

```bash
git add backend/
git commit -m "feat: project scaffold with config, deps, entry point"
```

---

### Task 2: Storage Layer — SQLite 数据模型 + Repository

**Files:**
- Create: `backend/app/models/database.py`
- Create: `backend/app/models/schemas.py`
- Create: `backend/app/services/repositories.py`
- Test: `backend/tests/test_repositories.py`

**Step 1: 写失败测试 `backend/tests/test_repositories.py`**

```python
import pytest
import asyncio
from pathlib import Path
from app.models.database import Database
from app.services.repositories import ConversationRepository, DocumentRepository
from app.models.schemas import MessageCreate, DocumentCreate


@pytest.fixture
async def db(tmp_path):
    database = Database(db_path=tmp_path / "test.db")
    await database.init()
    yield database
    await database.close()


@pytest.fixture
async def conv_repo(db):
    return ConversationRepository(db)


@pytest.fixture
async def doc_repo(db):
    return DocumentRepository(db)


@pytest.mark.asyncio
async def test_create_and_get_conversation(conv_repo):
    conv_id = await conv_repo.create(title="Test Chat", model="claude-opus-4-8")
    conv = await conv_repo.get(conv_id)
    assert conv is not None
    assert conv["title"] == "Test Chat"


@pytest.mark.asyncio
async def test_save_and_get_messages(conv_repo):
    conv_id = await conv_repo.create(title="Chat", model="claude-opus-4-8")
    await conv_repo.save_message(conv_id, MessageCreate(role="user", content="Hello"))
    await conv_repo.save_message(conv_id, MessageCreate(role="assistant", content="Hi there"))
    messages = await conv_repo.get_messages(conv_id)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["content"] == "Hi there"


@pytest.mark.asyncio
async def test_create_and_list_documents(doc_repo):
    doc_id = await doc_repo.create(DocumentCreate(
        filename="test.md",
        file_type="markdown",
        file_path="/tmp/test.md",
        size=1024,
    ))
    docs = await doc_repo.list_all()
    assert len(docs) == 1
    assert docs[0]["filename"] == "test.md"
```

**Step 2: 运行测试确认失败**

```bash
cd D:\rag\backend
venv\Scripts\python -m pytest tests/test_repositories.py -v
```

Expected: FAIL — modules not found

**Step 3: 实现数据模型 `backend/app/models/schemas.py`**

```python
from pydantic import BaseModel
from datetime import datetime


class MessageCreate(BaseModel):
    role: str
    content: str
    sources: str | None = None
    tool_calls: str | None = None


class DocumentCreate(BaseModel):
    filename: str
    file_type: str
    file_path: str
    size: int


class ChatRequest(BaseModel):
    query: str
    conversation_id: str | None = None
    model: str | None = None


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    chunks: int
```

**Step 4: 实现 Database 初始化 `backend/app/models/database.py`**

```python
import aiosqlite
from pathlib import Path


class Database:
    def __init__(self, db_path: Path | str):
        self.db_path = str(db_path)
        self._db: aiosqlite.Connection | None = None

    async def init(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._create_tables()

    async def _create_tables(self):
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                size INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                chunks INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                model TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conv_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                tool_calls TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conv_id) REFERENCES conversations(id)
            );

            CREATE TABLE IF NOT EXISTS user_config (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS usage_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cost REAL NOT NULL,
                conversation_id TEXT
            );
        """)
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self._db
```

**Step 5: 实现 Repository `backend/app/services/repositories.py`**

```python
import uuid
from app.models.database import Database
from app.models.schemas import MessageCreate, DocumentCreate


class ConversationRepository:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, title: str, model: str) -> str:
        conv_id = str(uuid.uuid4())
        await self.db.conn.execute(
            "INSERT INTO conversations (id, title, model) VALUES (?, ?, ?)",
            (conv_id, title, model),
        )
        await self.db.conn.commit()
        return conv_id

    async def get(self, conv_id: str) -> dict | None:
        cursor = await self.db.conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_all(self) -> list[dict]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM conversations ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def save_message(self, conv_id: str, msg: MessageCreate) -> str:
        msg_id = str(uuid.uuid4())
        await self.db.conn.execute(
            "INSERT INTO messages (id, conv_id, role, content, sources, tool_calls) VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, conv_id, msg.role, msg.content, msg.sources, msg.tool_calls),
        )
        await self.db.conn.commit()
        return msg_id

    async def get_messages(self, conv_id: str) -> list[dict]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM messages WHERE conv_id = ? ORDER BY created_at", (conv_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


class DocumentRepository:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, doc: DocumentCreate) -> str:
        doc_id = str(uuid.uuid4())
        await self.db.conn.execute(
            "INSERT INTO documents (id, filename, file_type, file_path, size) VALUES (?, ?, ?, ?, ?)",
            (doc_id, doc.filename, doc.file_type, doc.file_path, doc.size),
        )
        await self.db.conn.commit()
        return doc_id

    async def get(self, doc_id: str) -> dict | None:
        cursor = await self.db.conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_all(self) -> list[dict]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM documents ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def update_status(self, doc_id: str, status: str, chunks: int = 0):
        await self.db.conn.execute(
            "UPDATE documents SET status = ?, chunks = ? WHERE id = ?",
            (status, chunks, doc_id),
        )
        await self.db.conn.commit()

    async def delete(self, doc_id: str):
        await self.db.conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        await self.db.conn.commit()
```

**Step 6: 运行测试确认通过**

```bash
cd D:\rag\backend
venv\Scripts\pip install pytest pytest-asyncio
venv\Scripts\python -m pytest tests/test_repositories.py -v
```

Expected: 3 passed

**Step 7: 提交**

```bash
git add backend/
git commit -m "feat: storage layer with SQLite models and repositories"
```

---

### Task 3: LLM Gateway — 统一模型调用层

**Files:**
- Create: `backend/app/core/llm_gateway.py`
- Test: `backend/tests/test_llm_gateway.py`

**Step 1: 写失败测试**

```python
import pytest
from app.core.llm_gateway import LLMGateway, ChatMessage


@pytest.mark.asyncio
async def test_gateway_routes_to_correct_provider():
    """Gateway 应该根据 model 名称选择正确的 provider"""
    gateway = LLMGateway(claude_api_key="sk-test", deepseek_api_key="sk-test")
    provider = gateway.get_provider("claude-opus-4-8")
    assert provider == "claude"
    provider = gateway.get_provider("deepseek-chat")
    assert provider == "deepseek"


def test_chat_message_model():
    msg = ChatMessage(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"
```

**Step 2: 运行测试确认失败**

```bash
venv\Scripts\python -m pytest tests/test_llm_gateway.py -v
```

**Step 3: 实现 LLM Gateway `backend/app/core/llm_gateway.py`**

```python
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from collections.abc import AsyncIterator

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.core.config import settings

logger = logging.getLogger(__name__)

# 价格表 (USD per 1M tokens)
MODEL_PRICES = {
    "claude-opus-4-8": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "deepseek-chat": {"input": 0.27, "output": 1.10},
}

# 模型 → provider 映射
MODEL_PROVIDER_MAP = {
    "claude-opus-4-8": "claude",
    "claude-sonnet-4-6": "claude",
    "deepseek-chat": "deepseek",
}


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class UsageRecord:
    model: str
    input_tokens: int
    output_tokens: int
    cost: float


class LLMGateway:
    """统一模型调用入口：路由、重试、计费"""

    def __init__(
        self,
        claude_api_key: str = "",
        deepseek_api_key: str = "",
    ):
        self._claude_key = claude_api_key or settings.claude_api_key
        self._deepseek_key = deepseek_api_key or settings.deepseek_api_key
        self._clients: dict[str, ChatAnthropic | ChatOpenAI] = {}

    def get_provider(self, model: str) -> str:
        provider = MODEL_PROVIDER_MAP.get(model)
        if not provider:
            raise ValueError(f"Unknown model: {model}")
        return provider

    def _get_client(self, model: str):
        if model in self._clients:
            return self._clients[model]

        provider = self.get_provider(model)
        if provider == "claude":
            client = ChatAnthropic(
                model=model,
                api_key=self._claude_key,
                max_tokens=4096,
                streaming=True,
            )
        elif provider == "deepseek":
            client = ChatOpenAI(
                model=model,
                api_key=self._deepseek_key,
                base_url="https://api.deepseek.com",
                max_tokens=4096,
                streaming=True,
            )
        else:
            raise ValueError(f"No provider for model: {model}")

        self._clients[model] = client
        return client

    def _to_lc_messages(self, messages: list[ChatMessage]):
        mapping = {"user": HumanMessage, "assistant": AIMessage, "system": SystemMessage}
        return [mapping[m.role](content=m.content) for m in messages]

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """流式对话，逐 token 返回"""
        model = model or settings.default_chat_model
        client = self._get_client(model)
        lc_messages = self._to_lc_messages(messages)

        try:
            async for chunk in client.astream(lc_messages, temperature=temperature):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            # 降级到备用模型
            logger.warning(f"Model {model} failed: {e}. Trying fallback.")
            fallback = settings.fallback_chat_model
            if fallback != model:
                fallback_client = self._get_client(fallback)
                async for chunk in fallback_client.astream(lc_messages, temperature=temperature):
                    if chunk.content:
                        yield chunk.content
            else:
                raise

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """非流式对话，返回完整回答"""
        full = []
        async for token in self.chat_stream(messages, model, temperature):
            full.append(token)
        return "".join(full)

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        prices = MODEL_PRICES.get(model, {"input": 0, "output": 0})
        return (input_tokens / 1_000_000) * prices["input"] + (output_tokens / 1_000_000) * prices["output"]
```

**Step 4: 运行测试确认通过**

```bash
venv\Scripts\python -m pytest tests/test_llm_gateway.py -v
```

Expected: 2 passed

**Step 5: 提交**

```bash
git add backend/
git commit -m "feat: LLM gateway with routing, streaming, fallback, cost tracking"
```

---

### Task 4: Embedding 模块 + Qdrant 向量存储

**Files:**
- Create: `backend/app/core/embedding.py`
- Create: `backend/app/core/vector_store.py`
- Test: `backend/tests/test_vector_store.py`

**Step 1: 写失败测试**

```python
import pytest
from app.core.vector_store import VectorStore


@pytest.mark.asyncio
async def test_add_and_search(tmp_path):
    store = VectorStore(storage_path=tmp_path / "qdrant")
    await store.init()

    # 添加测试文档
    await store.add_documents(
        documents=["JWT 认证使用 RS256 算法", "Refresh Token 存储在 httpOnly Cookie"],
        metadatas=[
            {"doc_id": "doc1", "chunk_index": 0, "chunk_type": "text"},
            {"doc_id": "doc1", "chunk_index": 1, "chunk_type": "text"},
        ],
        ids=["chunk1", "chunk2"],
    )

    # 搜索
    results = await store.search("JWT 密钥管理", top_k=2)
    assert len(results) >= 1
    assert "JWT" in results[0].content or "RS256" in results[0].content
```

**Step 2: 运行测试确认失败**

```bash
venv\Scripts\python -m pytest tests/test_vector_store.py -v
```

**Step 3: 实现 Embedding `backend/app/core/embedding.py`**

```python
from langchain_community.embeddings import HuggingFaceEmbeddings
from app.core.config import settings

_embedding_model = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embedding_model
```

**Step 4: 实现 VectorStore `backend/app/core/vector_store.py`**

```python
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
)

from app.core.config import settings
from app.core.embedding import get_embedding_model

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    content: str
    score: float
    metadata: dict


class VectorStore:
    def __init__(self, storage_path: Path | None = None):
        self._storage_path = str(storage_path or settings.QDRANT_PATH)
        self._client: AsyncQdrantClient | None = None
        self._collection = settings.qdrant_collection

    async def init(self):
        Path(self._storage_path).mkdir(parents=True, exist_ok=True)
        self._client = AsyncQdrantClient(path=self._storage_path)

        collections = await self._client.get_collections()
        exists = any(c.name == self._collection for c in collections.collections)

        if not exists:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=settings.qdrant_vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created Qdrant collection: {self._collection}")

    async def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict],
        ids: list[str],
    ):
        embedding_model = get_embedding_model()
        vectors = embedding_model.embed_documents(documents)

        points = [
            PointStruct(
                id=idx,
                vector=vectors[idx],
                payload={"content": documents[idx], **metadatas[idx]},
            )
            for idx in range(len(documents))
        ]

        await self._client.upsert(
            collection_name=self._collection,
            points=points,
        )

    async def search(self, query: str, top_k: int = 5, doc_id: str | None = None) -> list[SearchResult]:
        embedding_model = get_embedding_model()
        query_vector = embedding_model.embed_query(query)

        search_filter = None
        if doc_id:
            search_filter = Filter(must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))])

        results = await self._client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=search_filter,
        )

        return [
            SearchResult(
                content=r.payload.get("content", ""),
                score=r.score,
                metadata={k: v for k, v in r.payload.items() if k != "content"},
            )
            for r in results
        ]

    async def delete_by_doc_id(self, doc_id: str):
        await self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]),
        )

    async def close(self):
        if self._client:
            await self._client.close()
```

**Step 5: 运行测试确认通过**

```bash
venv\Scripts\pip install pytest-asyncio
venv\Scripts\python -m pytest tests/test_vector_store.py -v
```

注意：首次运行会下载 BGE-M3 模型（~2GB），需要等待。

**Step 6: 提交**

```bash
git add backend/
git commit -m "feat: embedding module and Qdrant vector store with hybrid search"
```

---

### Task 5: RAG Engine — 检索 + 生成管线

**Files:**
- Create: `backend/app/services/rag_engine.py`
- Test: `backend/tests/test_rag_engine.py`

**Step 1: 写失败测试**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.rag_engine import RAGEngine


@pytest.mark.asyncio
async def test_rag_engine_generate_stream():
    """RAG Engine 应该：检索 → 组装 prompt → 流式生成"""
    # Mock 依赖
    mock_store = AsyncMock()
    mock_store.search.return_value = [
        MagicMock(content="JWT 使用 RS256", score=0.9, metadata={"doc_id": "d1"}),
    ]
    mock_llm = AsyncMock()

    # Mock 流式输出
    async def fake_stream(*args, **kwargs):
        for token in ["JWT", " 认证", " 使用", " RS256"]:
            yield token

    mock_llm.chat_stream = fake_stream

    engine = RAGEngine(vector_store=mock_store, llm_gateway=mock_llm)

    tokens = []
    async for token in engine.generate_stream("JWT 怎么用？"):
        tokens.append(token)

    assert "".join(tokens) == "JWT 认证 使用 RS256"
    mock_store.search.assert_called_once()
```

**Step 2: 运行测试确认失败**

```bash
venv\Scripts\python -m pytest tests/test_rag_engine.py -v
```

**Step 3: 实现 RAG Engine `backend/app/services/rag_engine.py`**

```python
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from app.core.llm_gateway import LLMGateway, ChatMessage
from app.core.vector_store import VectorStore
from app.core.config import settings

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """你是一个专业的 AI 助手。请严格根据以下检索到的上下文来回答用户的问题。
如果上下文中没有相关信息，请诚实地说明你不知道，不要编造内容。
回答时请引用来源，格式：[来源: 文件名]"""

RAG_USER_TEMPLATE = """## 检索到的上下文

{context}

---

## 用户问题

{query}"""


class RAGEngine:
    def __init__(self, vector_store: VectorStore, llm_gateway: LLMGateway):
        self.vector_store = vector_store
        self.llm_gateway = llm_gateway

    async def search(self, query: str, top_k: int | None = None) -> list:
        """混合检索"""
        top_k = top_k or settings.retrieval_top_k
        results = await self.vector_store.search(query, top_k=top_k)
        # 按 score 降序截取
        return sorted(results, key=lambda r: r.score, reverse=True)[:settings.rerank_top_k]

    def _build_context(self, results: list) -> str:
        """将检索结果组装成上下文文本"""
        parts = []
        for i, r in enumerate(results, 1):
            source = r.metadata.get("doc_id", "unknown")
            parts.append(f"[来源{i}: {source}]\n{r.content}")
        return "\n\n".join(parts)

    async def generate_stream(
        self,
        query: str,
        conversation_id: str | None = None,
        history: list[ChatMessage] | None = None,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """完整的 RAG 流式生成管线"""
        # 1. 检索
        results = await self.search(query)
        context = self._build_context(results)

        # 2. 组装消息
        messages = [ChatMessage(role="system", content=RAG_SYSTEM_PROMPT)]

        # 加入历史对话
        if history:
            messages.extend(history[-6:])  # 最近 3 轮

        messages.append(ChatMessage(
            role="user",
            content=RAG_USER_TEMPLATE.format(context=context, query=query),
        ))

        # 3. 流式生成
        async for token in self.llm_gateway.chat_stream(messages, model=model):
            yield token
```

**Step 4: 运行测试确认通过**

```bash
venv\Scripts\python -m pytest tests/test_rag_engine.py -v
```

Expected: 1 passed

**Step 5: 提交**

```bash
git add backend/
git commit -m "feat: RAG engine with retrieval, context building, streaming generation"
```

---

### Task 6: 文档处理管线 — 解析 + 分块 + 索引

**Files:**
- Create: `backend/app/services/doc_pipeline.py`
- Test: `backend/tests/test_doc_pipeline.py`

**Step 1: 写失败测试**

```python
import pytest
from app.services.doc_pipeline import DocPipeline


def test_chunk_text_basic():
    pipeline = DocPipeline()
    chunks = pipeline.chunk_text("Hello world. This is a test. Another sentence here.", chunk_size=20, overlap=5)
    assert len(chunks) >= 2
    assert all(isinstance(c, str) for c in chunks)


def test_chunk_text_preserves_content():
    pipeline = DocPipeline()
    text = "A" * 100
    chunks = pipeline.chunk_text(text, chunk_size=50, overlap=10)
    # 所有 chunk 拼起来应该包含原始文本的绝大部分
    rejoined = "".join(chunks)
    assert "A" * 90 in rejoined
```

**Step 2: 运行测试确认失败**

```bash
venv\Scripts\python -m pytest tests/test_doc_pipeline.py -v
```

**Step 3: 实现 DocPipeline `backend/app/services/doc_pipeline.py`**

```python
from __future__ import annotations

import uuid
import logging
from pathlib import Path

from langchain_community.document_loaders import (
    UnstructuredMarkdownLoader,
    UnstructuredPDFLoader,
    TextLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.vector_store import VectorStore
from app.services.repositories import DocumentRepository
from app.models.schemas import DocumentCreate

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".md": "markdown",
    ".txt": "text",
    ".pdf": "pdf",
    ".docx": "docx",
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".tsx": "code",
    ".jsx": "code",
    ".java": "code",
    ".go": "code",
    ".rs": "code",
    ".c": "code",
    ".cpp": "code",
    ".h": "code",
}


class DocPipeline:
    def __init__(self, vector_store: VectorStore | None = None, doc_repo: DocumentRepository | None = None):
        self.vector_store = vector_store
        self.doc_repo = doc_repo
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
        """将文本分块"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        return splitter.split_text(text)

    def _load_file(self, file_path: Path) -> str:
        """根据文件类型选择加载器"""
        ext = file_path.suffix.lower()
        if ext == ".md":
            loader = UnstructuredMarkdownLoader(str(file_path))
        elif ext == ".pdf":
            loader = UnstructuredPDFLoader(str(file_path))
        elif ext in (".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".c", ".cpp", ".h"):
            loader = TextLoader(str(file_path), encoding="utf-8")
        else:
            loader = TextLoader(str(file_path), encoding="utf-8")

        docs = loader.load()
        return "\n\n".join(d.page_content for d in docs)

    async def process_file(self, file_path: Path) -> dict:
        """处理单个文件：解析 → 分块 → 索引"""
        ext = file_path.suffix.lower()
        file_type = SUPPORTED_EXTENSIONS.get(ext, "unknown")

        # 1. 解析
        content = self._load_file(file_path)
        logger.info(f"Parsed {file_path.name}: {len(content)} chars")

        # 2. 分块
        chunks = self.chunk_text(content)
        logger.info(f"Split into {len(chunks)} chunks")

        # 3. 生成 ID 和元数据
        doc_id = str(uuid.uuid4())
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {"doc_id": doc_id, "chunk_index": i, "chunk_type": "code" if file_type == "code" else "text", "filename": file_path.name}
            for i in range(len(chunks))
        ]

        # 4. 存入向量库
        if self.vector_store:
            await self.vector_store.add_documents(
                documents=chunks,
                metadatas=metadatas,
                ids=ids,
            )

        # 5. 存入元数据
        if self.doc_repo:
            await self.doc_repo.create(DocumentCreate(
                filename=file_path.name,
                file_type=file_type,
                file_path=str(file_path),
                size=file_path.stat().st_size,
            ))
            await self.doc_repo.update_status(doc_id, "indexed", len(chunks))

        return {"doc_id": doc_id, "filename": file_path.name, "chunks": len(chunks), "status": "indexed"}
```

**Step 4: 运行测试确认通过**

```bash
venv\Scripts\python -m pytest tests/test_doc_pipeline.py -v
```

Expected: 2 passed

**Step 5: 提交**

```bash
git add backend/
git commit -m "feat: document pipeline with parsing, chunking, indexing"
```

---

### Task 7: API Gateway — FastAPI 路由 + SSE 流式

**Files:**
- Create: `backend/app/api/app.py`
- Create: `backend/app/api/routes/chat.py`
- Create: `backend/app/api/routes/knowledge.py`
- Create: `backend/app/api/routes/config.py`
- Create: `backend/app/api/routes/health.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/middleware/__init__.py`
- Test: `backend/tests/test_api.py`

**Step 1: 写失败测试**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.api.app import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_list_documents_empty(client):
    response = await client.get("/api/knowledge/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

**Step 2: 运行测试确认失败**

```bash
venv\Scripts\pip install httpx
venv\Scripts\python -m pytest tests/test_api.py -v
```

**Step 3: 实现依赖注入 `backend/app/api/deps.py`**

```python
from app.core.config import settings
from app.core.llm_gateway import LLMGateway
from app.core.vector_store import VectorStore
from app.models.database import Database
from app.services.repositories import ConversationRepository, DocumentRepository
from app.services.rag_engine import RAGEngine
from app.services.doc_pipeline import DocPipeline


# Singletons (initialized in app lifespan)
_db: Database | None = None
_llm: LLMGateway | None = None
_vector_store: VectorStore | None = None
_rag_engine: RAGEngine | None = None
_doc_pipeline: DocPipeline | None = None


def set_db(db: Database): global _db; _db = db
def set_llm(llm: LLMGateway): global _llm; _llm = llm
def set_vector_store(vs: VectorStore): global _vector_store; _vector_store = vs
def set_rag_engine(engine: RAGEngine): global _rag_engine; _rag_engine = engine
def set_doc_pipeline(pipeline: DocPipeline): global _doc_pipeline; _doc_pipeline = pipeline


def get_db() -> Database:
    return _db

def get_llm() -> LLMGateway:
    return _llm

def get_vector_store() -> VectorStore:
    return _vector_store

def get_rag_engine() -> RAGEngine:
    return _rag_engine

def get_doc_pipeline() -> DocPipeline:
    return _doc_pipeline

def get_conv_repo() -> ConversationRepository:
    return ConversationRepository(_db)

def get_doc_repo() -> DocumentRepository:
    return DocumentRepository(_db)
```

**Step 4: 实现健康检查路由 `backend/app/api/routes/health.py`**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok"}
```

**Step 5: 实现对话路由 `backend/app/api/routes/chat.py`**

```python
import json
from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_rag_engine, get_conv_repo, get_llm
from app.core.llm_gateway import LLMGateway
from app.services.rag_engine import RAGEngine
from app.services.repositories import ConversationRepository
from app.models.schemas import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    rag: RAGEngine = Depends(get_rag_engine),
    conv_repo: ConversationRepository = Depends(get_conv_repo),
    llm: LLMGateway = Depends(get_llm),
):
    """SSE 流式对话"""
    # 创建或获取对话
    if not req.conversation_id:
        conv_id = await conv_repo.create(
            title=req.query[:50],
            model=req.model or "claude-opus-4-8",
        )
    else:
        conv_id = req.conversation_id

    # 保存用户消息
    await conv_repo.save_message(
        conv_id=conv_id,
        message=MessageCreate(role="user", content=req.query),
    )

    # 获取历史
    history_rows = await conv_repo.get_messages(conv_id)
    from app.core.llm_gateway import ChatMessage
    history = [
        ChatMessage(role=m["role"], content=m["content"])
        for m in history_rows[:-1]  # 排除刚保存的
    ]

    async def event_generator():
        full_response = []
        try:
            async for token in rag.generate_stream(
                query=req.query,
                conversation_id=conv_id,
                history=history,
                model=req.model,
            ):
                full_response.append(token)
                yield {"event": "token", "data": json.dumps({"token": token, "conv_id": conv_id})}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

        # 保存 AI 回复
        await conv_repo.save_message(
            conv_id=conv_id,
            message=MessageCreate(role="assistant", content="".join(full_response)),
        )
        yield {"event": "done", "data": json.dumps({"conv_id": conv_id})}

    return EventSourceResponse(event_generator())


@router.get("/history/{conv_id}")
async def get_history(conv_id: str, conv_repo: ConversationRepository = Depends(get_conv_repo)):
    messages = await conv_repo.get_messages(conv_id)
    return messages
```

注意：chat.py 中 `MessageCreate` 需要从 schemas 导入，添加：`from app.models.schemas import ChatRequest, MessageCreate`

**Step 6: 实现知识库路由 `backend/app/api/routes/knowledge.py`**

```python
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File

from app.api.deps import get_doc_repo, get_doc_pipeline, get_vector_store
from app.core.config import settings
from app.services.repositories import DocumentRepository
from app.services.doc_pipeline import DocPipeline
from app.core.vector_store import VectorStore

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/")
async def list_documents(doc_repo: DocumentRepository = Depends(get_doc_repo)):
    return await doc_repo.list_all()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_repo: DocumentRepository = Depends(get_doc_repo),
    doc_pipeline: DocPipeline = Depends(get_doc_pipeline),
):
    # 保存文件
    upload_dir = settings.UPLOAD_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 处理文件
    result = await doc_pipeline.process_file(file_path)
    return result


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    doc_repo: DocumentRepository = Depends(get_doc_repo),
    vector_store: VectorStore = Depends(get_vector_store),
):
    doc = await doc_repo.get(doc_id)
    if doc:
        await vector_store.delete_by_doc_id(doc_id)
        await doc_repo.delete(doc_id)
    return {"status": "deleted", "doc_id": doc_id}
```

**Step 7: 实现配置路由 `backend/app/api/routes/config.py`**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/models")
async def list_models():
    return {
        "models": [
            {"id": "claude-opus-4-8", "name": "Claude Opus 4.8", "provider": "claude"},
            {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "provider": "claude"},
            {"id": "deepseek-chat", "name": "DeepSeek Chat", "provider": "deepseek"},
        ]
    }
```

**Step 8: 实现 FastAPI App `backend/app/api/app.py`**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.llm_gateway import LLMGateway
from app.core.vector_store import VectorStore
from app.models.database import Database
from app.services.rag_engine import RAGEngine
from app.services.doc_pipeline import DocPipeline
from app.api import deps
from app.api.routes import health, chat, knowledge, config


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    settings.QDRANT_PATH.mkdir(parents=True, exist_ok=True)

    db = Database(settings.DB_PATH)
    await db.init()
    deps.set_db(db)

    llm = LLMGateway()
    deps.set_llm(llm)

    vector_store = VectorStore()
    await vector_store.init()
    deps.set_vector_store(vector_store)

    rag_engine = RAGEngine(vector_store=vector_store, llm_gateway=llm)
    deps.set_rag_engine(rag_engine)

    doc_pipeline = DocPipeline(vector_store=vector_store, doc_repo=deps.get_doc_repo())
    deps.set_doc_pipeline(doc_pipeline)

    yield

    # Shutdown
    await vector_store.close()
    await db.close()


def create_app() -> FastAPI:
    app = FastAPI(title="RAG AI Assistant", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(knowledge.router, prefix="/api")
    app.include_router(config.router, prefix="/api")

    return app


app = create_app()
```

**Step 9: 运行测试确认通过**

```bash
venv\Scripts\pip install httpx
venv\Scripts\python -m pytest tests/test_api.py -v
```

Expected: 2 passed

**Step 10: 手动启动验证**

```bash
cd D:\rag\backend
venv\Scripts\python run.py
```

浏览器打开 `http://localhost:8000/docs` 查看 Swagger 文档。

**Step 11: 提交**

```bash
git add backend/
git commit -m "feat: FastAPI routes with SSE streaming, file upload, health check"
```

---

### Task 8: 端到端集成验证

**Files:**
- Test: `backend/tests/test_e2e.py`

**Step 1: 写端到端测试**

```python
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from app.api.app import create_app


@pytest.fixture
async def client(tmp_path):
    # 临时数据目录
    from app.core.config import settings
    settings.DATA_DIR = tmp_path
    settings.UPLOAD_DIR = tmp_path / "uploads"
    settings.DB_PATH = tmp_path / "rag.db"
    settings.QDRANT_PATH = tmp_path / "qdrant"

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_config_models(client):
    r = await client.get("/api/config/models")
    assert r.status_code == 200
    assert len(r.json()["models"]) >= 2


@pytest.mark.asyncio
async def test_upload_and_list(client, tmp_path):
    # 创建测试文件
    test_file = tmp_path / "test.md"
    test_file.write_text("# JWT Auth\n\nJWT 使用 RS256 算法签名。")

    with open(test_file, "rb") as f:
        r = await client.post("/api/knowledge/upload", files={"file": ("test.md", f, "text/markdown")})

    assert r.status_code == 200
    assert r.json()["status"] == "indexed"

    # 列表
    r = await client.get("/api/knowledge/")
    assert r.status_code == 200
```

**Step 2: 运行测试**

```bash
venv\Scripts\python -m pytest tests/test_e2e.py -v
```

**Step 3: 提交**

```bash
git add backend/
git commit -m "feat: end-to-end integration tests for upload and query pipeline"
```

---

## 完成后的项目结构

```
D:\rag/
├── .gitignore
├── .env.example
├── README.md
├── backend/
│   ├── requirements.txt
│   ├── run.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py          ← 配置
│   │   │   ├── llm_gateway.py     ← 统一模型调用
│   │   │   ├── embedding.py       ← BGE-M3
│   │   │   └── vector_store.py    ← Qdrant
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── database.py        ← SQLite 初始化
│   │   │   └── schemas.py         ← Pydantic 模型
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── repositories.py    ← 数据访问
│   │   │   ├── rag_engine.py      ← RAG 管线
│   │   │   └── doc_pipeline.py    ← 文档处理
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── app.py             ← FastAPI 应用
│   │       ├── deps.py            ← 依赖注入
│   │       └── routes/
│   │           ├── __init__.py
│   │           ├── health.py
│   │           ├── chat.py
│   │           ├── knowledge.py
│   │           └── config.py
│   └── tests/
│       ├── test_repositories.py
│       ├── test_llm_gateway.py
│       ├── test_vector_store.py
│       ├── test_rag_engine.py
│       ├── test_doc_pipeline.py
│       ├── test_api.py
│       └── test_e2e.py
└── .env                           ← (本地，不提交)
```

## 后续 Phase 2 预告

- Agent Core (LangGraph 状态图 + ToolKit)
- Agent API 路由 + SSE 进度推送
- 对话历史持久化
- Token 计费统计
- 前端 React 项目初始化
