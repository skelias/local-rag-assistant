"""知识库 API 测试：上传 → 预览 → 确认 → 删除。

全部用假组件注入（临时 DB + FakeEmbedder 的 QdrantStore），不碰真实 data/ 目录、不联网。
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.app import create_app
from app.core.embedding import EmbeddingProvider
from app.core.vector_store import QdrantStore


class FakeEmbedder(EmbeddingProvider):
    dim = 64

    async def encode_dense(self, texts):
        import hashlib
        out = []
        for t in texts:
            h = hashlib.sha256(t.encode()).digest()
            out.append([h[i % 32] / 255.0 for i in range(64)])
        return out

    async def encode_sparse(self, texts):
        out = []
        for t in texts:
            d = {}
            for ch in t:
                tok = (ord(ch) % 500) + 1
                d[tok] = d.get(tok, 0.0) + 1.0
            out.append(d)
        return out


@pytest.fixture
async def client(tmp_path):
    from app.models.database import Database

    db = Database(tmp_path / "api.db")
    await db.init()
    store = QdrantStore(path=tmp_path / "q", collection="t", vector_size=64,
                        embedder=FakeEmbedder())
    await store.init()

    app = create_app(db=db, vector_store=store, upload_dir=tmp_path / "uploads")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c

    await store.close()
    await db.close()


async def _upload_md(client, content: str, name="guide.md"):
    return await client.post(
        "/api/knowledge/1/documents",
        files={"file": (name, content.encode("utf-8"), "text/markdown")},
    )


async def test_upload_parses_and_marks_parsed(client):
    r = await _upload_md(client, "# 指南\n\nQdrant 本地模式。\n\nRRF 融合。")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "parsed"
    assert body["pending_chunks"] >= 2


async def test_unsupported_ext_rejected(client):
    r = await client.post(
        "/api/knowledge/1/documents",
        files={"file": ("evil.exe", b"MZ...", "application/octet-stream")},
    )
    assert r.status_code == 415


async def test_preview_returns_pending_chunks(client):
    up = await _upload_md(client, "# 标题\n\n第一段。\n\n第二段。")
    doc_id = up.json()["id"]

    pv = await client.get(f"/api/knowledge/1/documents/{doc_id}/preview")
    assert pv.status_code == 200
    chunks = pv.json()["chunks"]
    assert len(chunks) >= 2
    assert all("text" in c for c in chunks)


async def test_confirm_indexes_then_list_shows_ready(client):
    up = await _upload_md(client, "# 指南\n\nQdrant 用 RRF 融合两路召回。")
    doc_id = up.json()["id"]

    cf = await client.post(f"/api/knowledge/1/documents/{doc_id}/confirm")
    assert cf.status_code == 200
    assert cf.json()["status"] == "ready"

    lst = await client.get("/api/knowledge/1/documents")
    doc = [d for d in lst.json() if d["id"] == doc_id][0]
    assert doc["status"] == "ready"
    assert doc["chunk_count"] > 0


async def test_delete_removes_document(client):
    up = await _upload_md(client, "# 将被删除\n\n内容。")
    doc_id = up.json()["id"]
    await client.post(f"/api/knowledge/1/documents/{doc_id}/confirm")

    d = await client.delete(f"/api/knowledge/1/documents/{doc_id}")
    assert d.status_code == 200

    lst = await client.get("/api/knowledge/1/documents")
    assert all(x["id"] != doc_id for x in lst.json())
