"""对话/命中测试/配置 API 测试：全链路（上传→确认→提问 SSE→命中测试→配置）。

全部假组件：临时 DB + FakeEmbedder 的 QdrantStore + 固定回一句的 FakeGateway。
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.app import create_app
from app.core.embedding import EmbeddingProvider
from app.core.vector_store import QdrantStore
from app.services.repositories import ConversationRepository


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


class FakeGateway:
    """固定回一句"基于来源的假回答"，并带 token 用量。"""
    async def stream(self, messages):
        for m in messages:
            if m.role == "user":
                yield type("U", (), {"text": "这是假模型基于来源的回答。", "out_tokens": 9,
                                     "hit_tokens": 0, "miss_tokens": 3, "fallback": False})()


@pytest.fixture
async def ctx(tmp_path):
    from app.models.database import Database

    db = Database(tmp_path / "api.db")
    await db.init()
    store = QdrantStore(path=tmp_path / "q", collection="t", vector_size=64,
                        embedder=FakeEmbedder())
    await store.init()
    app = create_app(db=db, vector_store=store, upload_dir=tmp_path / "uploads",
                     chat_gateway=FakeGateway())
    yield app, db
    await store.close()
    await db.close()


@pytest.fixture
async def client(ctx):
    app, _ = ctx
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def _index_one_doc(client, content="# 指南\n\nQdrant 用 RRF 融合两路召回文档。",
                         name="guide.md") -> int:
    up = await client.post(
        "/api/knowledge/1/documents",
        files={"file": (name, content.encode("utf-8"), "text/markdown")},
    )
    assert up.status_code == 201, up.text
    doc_id = up.json()["id"]
    cf = await client.post(f"/api/knowledge/1/documents/{doc_id}/confirm")
    assert cf.status_code == 200, cf.text
    return doc_id


async def test_chat_stream_emits_sources_tokens_done(client):
    await _index_one_doc(client, "# 指南\n\nQdrant 用 RRF 融合两路召回。")

    async with client.stream("POST", "/api/chat/stream",
                             json={"kb_id": 1, "query": "Qdrant 怎么融合？"}) as resp:
        assert resp.status_code == 200
        body = (await resp.aread()).decode("utf-8")

    assert "event: sources" in body
    assert '"n": 1' in body
    assert "event: token" in body
    assert "假模型" in body
    assert "event: done" in body


async def test_chat_persists_conversation(ctx, client):
    app, db = ctx
    await _index_one_doc(client, "# 指南\n\n内容。")

    async with client.stream("POST", "/api/chat/stream",
                             json={"kb_id": 1, "query": "你好"}) as resp:
        body = (await resp.aread()).decode("utf-8")
    assert "event: done" in body

    conv_repo = ConversationRepository(db)
    rows = await conv_repo.list(kb_id=1)
    assert len(rows) == 1
    conv_id = rows[0]["id"]
    msgs = await conv_repo.get_messages(conv_id)
    assert len(msgs) == 2                       # user + assistant
    assert msgs[0]["role"] == "user"
    assert "假模型" in msgs[1]["content"]
    assert msgs[1]["sources"], "assistant 消息应带 sources"


async def test_hit_test_shares_params_and_returns_hits(client):
    await _index_one_doc(client, "# Qdrant\n\nRRF 融合两路召回，代码文档检索靠 BM25 精确命中。")

    r = await client.post("/api/knowledge/1/hit-test", json={"query": "RRF 融合"})
    assert r.status_code == 200
    body = r.json()
    assert body["params"]["top_k"] == 20                    # 默认参数
    assert body["hits"], "应能命中刚入库的文档"
    assert "score_breakdown" in body["hits"][0]


async def test_config_get_put(client):
    r = await client.put("/api/config", json={"key": "kb.1.retrieval.top_k", "value": 8})
    assert r.status_code == 200

    g = await client.get("/api/config")
    assert g.json()["kb.1.retrieval.top_k"] == 8
