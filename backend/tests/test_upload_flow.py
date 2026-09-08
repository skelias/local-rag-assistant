"""上传→解析→预览→确认 全流程测试（纯本地：临时 DB + 假向量存储）。

验证三个新函数：
- save_upload            文件真正落到 data/uploads/kb{id}/
- run_upload_pipeline    解析+分块写进 SQLite(pending)，返回块数
- confirm_document_index 确认后：向量库收到同样的块、chunks 标记 indexed、文档 ready
"""
from pathlib import Path

import pytest

from app.models.database import Database
from app.models.schemas import DocumentCreate
from app.services.doc_pipeline import (
    confirm_document_index,
    run_upload_pipeline,
    save_upload,
)
from app.services.repositories import ChunkRepository, DocumentRepository


class RecordingStore:
    """假的 QdrantStore：只记录收到了哪些块，不真存。"""

    def __init__(self):
        self.received: list[dict] = []

    async def upsert_chunks(self, chunks: list[dict]) -> None:
        self.received.extend(chunks)


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "t.db")
    await database.init()
    yield database
    await database.close()


@pytest.fixture
async def docs(db):
    return DocumentRepository(db)


@pytest.fixture
async def chunks(db):
    return ChunkRepository(db)


async def _new_doc(docs, tmp_path, filename="guide.md"):
    doc_id = await docs.create(DocumentCreate(
        kb_id=1, filename=filename, file_type=Path(filename).suffix,
        file_path=str(tmp_path / filename), size=0,
    ))
    return doc_id


async def test_save_upload_writes_into_kb_folder(tmp_path):
    dest = save_upload(b"hello content", "guide.md", kb_id=2, base_dir=tmp_path)
    assert dest.exists()
    assert dest.parent.name == "kb2"          # 落在 kb2 专属文件夹
    assert dest.read_bytes() == b"hello content"


async def test_upload_pipeline_writes_pending_chunks(tmp_path, docs, chunks):
    src = tmp_path / "guide.md"
    src.write_text("# 指南\n\nQdrant 用本地模式。\n\nRRF 融合多路召回。", encoding="utf-8")

    doc_id = await _new_doc(docs, tmp_path)
    count = await run_upload_pipeline(src, chunks, doc_id=doc_id, kb_id=1)

    assert count >= 2                          # 标题 + 两段 → 至少两三个块
    rows = await chunks.list_pending(doc_id)
    assert rows[0]["meta"]["file"] == "guide.md"
    assert rows[0]["status"] == "pending"      # 待确认，还没入向量库
    assert any("RRF" in r["text"] for r in rows)


async def test_upload_pipeline_python_code_uses_line_batches(tmp_path, docs, chunks):
    src = tmp_path / "demo.py"
    src.write_text("".join(f"def f{i}():\n    return {i}\n\n" for i in range(30)), encoding="utf-8")

    doc_id = await _new_doc(docs, tmp_path, filename="demo.py")
    count = await run_upload_pipeline(src, chunks, doc_id=doc_id, kb_id=1)

    assert count >= 2
    rows = await chunks.list_pending(doc_id)
    assert rows[0]["meta"]["lang"] == "py"


async def test_confirm_indexes_and_marks_ready(tmp_path, docs, chunks):
    src = tmp_path / "guide.md"
    src.write_text("# 指南\n\n内容若干。", encoding="utf-8")
    doc_id = await _new_doc(docs, tmp_path)
    await run_upload_pipeline(src, chunks, doc_id=doc_id, kb_id=1)

    store = RecordingStore()
    await confirm_document_index(doc_id=doc_id, kb_id=1, doc_repo=docs,
                                 chunk_repo=chunks, store=store)

    assert len(store.received) >= 1            # 向量库收到了块
    assert {c["id"] for c in store.received} == {r["id"] for r in await chunks.list_all(doc_id)}
    all_rows = await chunks.list_all(doc_id)
    assert all(r["status"] == "indexed" for r in all_rows)   # 标记已入向量库
    doc = await docs.get(doc_id)
    assert doc["status"] == "ready"            # 文档可用
