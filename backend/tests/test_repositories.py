"""Repository 层测试：ConversationRepository / DocumentRepository 能干活。

fixture（夹具）：pytest 里用 @pytest.fixture 定义"每场测试前先准备的东西"。
这里准备一个连到临时目录的 Database，以及两个"管理员"对象。
"""
import pytest

from app.models.database import Database
from app.models.schemas import DocumentCreate, MessageCreate
from app.services.repositories import (
    ChunkRepository,
    ConfigRepository,
    ConversationRepository,
    DocumentRepository,
    UsageRepository,
)


@pytest.fixture
async def db(tmp_path):
    """每个测试一个独立临时数据库文件。"""
    database = Database(tmp_path / "test.db")
    await database.init()
    yield database          # yield = 把东西交给测试；测试结束后回到这里
    await database.close()  # 清理


@pytest.fixture
async def conv(db):
    return ConversationRepository(db)


@pytest.fixture
async def docs(db):
    return DocumentRepository(db)


@pytest.fixture
async def chunks(db):
    return ChunkRepository(db)


@pytest.fixture
async def cfg(db):
    return ConfigRepository(db)


@pytest.fixture
async def usage(db):
    return UsageRepository(db)


# ---------- 对话 + 消息 ----------

async def test_create_and_get_conversation(conv):
    conv_id = await conv.create(title="第一场", model="claude-sonnet-4-5", kb_id=1)
    assert isinstance(conv_id, int) and conv_id > 0

    rows = await conv.list(kb_id=1)
    assert rows[0]["title"] == "第一场"


async def test_save_and_get_messages(conv):
    conv_id = await conv.create(title="对话", model="claude-sonnet-4-5", kb_id=1)

    await conv.save_message(conv_id, MessageCreate(role="user", content="你好"))
    # AI 回答带来源引用（sources 是列表，里面是字典）
    await conv.save_message(conv_id, MessageCreate(
        role="assistant", content="你好！",
        sources=[{"n": 1, "chunk_id": 9, "file": "guide.md", "score": 0.8}],
    ))

    msgs = await conv.get_messages(conv_id)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["content"] == "你好！"
    # sources 存进数据库时被转成了 JSON 字符串，读出来要还原成列表
    assert msgs[1]["sources"][0]["chunk_id"] == 9


# ---------- 文档 + 状态机 ----------

async def test_create_document_and_status_machine(docs):
    doc_id = await docs.create(DocumentCreate(
        kb_id=1, filename="guide.md", file_type=".md",
        file_path="C:/fake/guide.md", size=1024,
    ))
    # 状态机：uploading → parsed → ready
    await docs.set_status(doc_id, "parsed")
    await docs.set_status(doc_id, "ready")

    doc = await docs.get(doc_id)
    assert doc is not None
    assert doc["status"] == "ready"
    assert doc["filename"] == "guide.md"

    lst = await docs.list_by_kb(1)
    assert len(lst) == 1
    assert lst[0]["chunk_count"] == 0     # 还没分块


async def test_delete_conversation_cascades(conv):
    """删对话后，它的消息也一起没了（外键 ON DELETE CASCADE）。"""
    conv_id = await conv.create(title="要删的", model="m", kb_id=1)
    await conv.save_message(conv_id, MessageCreate(role="user", content="hi"))
    await conv.delete(conv_id)

    msgs = await conv.get_messages(conv_id)
    assert msgs == []


# ---------- 分块 ----------

async def test_chunk_insert_and_read_pending(chunks, docs):
    # 分块必须挂在真实存在的文档下（外键约束！）—— 先建一篇文档
    doc_id = await docs.create(DocumentCreate(
        kb_id=1, filename="a.md", file_type=".md",
        file_path="C:/fake/a.md", size=1,
    ))

    # 先清空旧块（模拟"重新解析前删旧块"），再写入两块
    await chunks.delete_by_document(doc_id=doc_id)
    await chunks.insert_many([
        {"kb_id": 1, "document_id": doc_id, "seq": 0, "text": "第一块", "meta": {"page": 1}},
        {"kb_id": 1, "document_id": doc_id, "seq": 1, "text": "第二块", "meta": {}},
    ])

    rows = await chunks.list_pending(doc_id=doc_id)
    assert len(rows) == 2
    assert rows[0]["text"] == "第一块"
    assert rows[0]["meta"]["page"] == 1          # meta 存了 JSON，读回是字典


async def test_chunk_mark_indexed(chunks, docs):
    doc_id = await docs.create(DocumentCreate(
        kb_id=1, filename="b.md", file_type=".md",
        file_path="C:/fake/b.md", size=1,
    ))
    await chunks.insert_many([{"kb_id": 1, "document_id": doc_id, "seq": 0, "text": "x", "meta": {}}])
    await chunks.mark_indexed(doc_id=doc_id)

    all_rows = await chunks.list_all(doc_id=doc_id)
    assert all_rows[0]["status"] == "indexed"


# ---------- 设置 ----------

async def test_config_get_default_then_set(cfg):
    # 没设置过时返回默认值
    assert await cfg.get("llm.provider", default="anthropic") == "anthropic"

    # 设置后再读，返回设置的值
    await cfg.set("llm.provider", "deepseek")
    assert await cfg.get("llm.provider") == "deepseek"

    # all() 把所有设置倒出来（以后"设置页"就是从这读的）
    everything = await cfg.all()
    assert everything["llm.provider"] == "deepseek"


# ---------- 用量 ----------

async def test_usage_record_and_summary(usage):
    await usage.record(model="claude-sonnet-4-5", input_tokens=100, output_tokens=50, cost=0.0042)
    await usage.record(model="deepseek-chat", input_tokens=10, output_tokens=5, cost=0.00001)

    s = await usage.summary()
    assert s["requests"] == 2
    assert round(s["cost"], 5) == round(0.0042 + 0.00001, 5)
    assert s["input_tokens"] == 110
