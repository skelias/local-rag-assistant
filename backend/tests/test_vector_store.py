"""向量存储层测试：Qdrant(本地文件) 能存分块、能混合检索(RRF)、能删。

全程用 FakeEmbedder（确定性向量，不下载模型、不联网）。
"""
import pytest

from app.core.embedding import EmbeddingProvider
from app.core.vector_store import QdrantStore


class FakeEmbedder(EmbeddingProvider):
    """确定性假向量：文本里的每个字符映射一个 token（稀疏），稠密向量也按文本算。

    设计成"字符相同 → token 相同"，这样含相同字的两段文本能被两路都召回。
    """
    dim = 64

    async def encode_dense(self, texts: list[str]) -> list[list[float]]:
        import hashlib
        out = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            out.append([h[i % 32] / 255.0 for i in range(self.dim)])
        return out

    async def encode_sparse(self, texts: list[str]) -> list[dict[int, float]]:
        out = []
        for t in texts:
            counts: dict[int, float] = {}
            for ch in t:
                tok = (ord(ch) % 500) + 1          # 字符 → 一个 token id（1..500）
                counts[tok] = counts.get(tok, 0.0) + 1.0
            out.append(counts)
        return out


@pytest.fixture
async def store(tmp_path):
    s = QdrantStore(path=tmp_path / "qdrant", collection="t",
                    vector_size=64, embedder=FakeEmbedder())
    await s.init()
    yield s
    await s.close()


async def test_upsert_and_hybrid_search_returns_breakdown(store):
    await store.upsert_chunks([
        {"id": 1, "kb_id": 1, "document_id": 10, "seq": 0,
         "text": "FastAPI 异步路由与依赖注入", "meta": {"file": "a.md"}},
        {"id": 2, "kb_id": 1, "document_id": 10, "seq": 1,
         "text": "Qdrant 本地模式与 RRF 融合", "meta": {"file": "a.md"}},
    ])
    hits = await store.hybrid_search(query="Qdrant RRF 融合", kb_id=1, top_k=5,
                                     dense_prefetch=10, sparse_prefetch=10, threshold=0.0)
    assert hits, "应当能搜到东西"
    assert hits[0].document_id == 10
    assert "rrf" in hits[0].score_breakdown
    # 至少一路给出细分分数
    assert ("vector" in hits[0].score_breakdown) or ("bm25" in hits[0].score_breakdown)


async def test_threshold_keeps_only_strong_hits(store):
    # 两个分块：一个与查询几乎完全相同（强），一个完全不同（弱）
    await store.upsert_chunks([
        {"id": 1, "kb_id": 1, "document_id": 10, "seq": 0,
         "text": "Qdrant 本地模式与 RRF 融合检索", "meta": {"file": "a.md"}},
        {"id": 2, "kb_id": 1, "document_id": 10, "seq": 1,
         "text": "今天天气不错适合散步", "meta": {"file": "a.md"}},
    ])

    # 阈值 0：两条都可能回来（不强求）
    loose = await store.hybrid_search(query="Qdrant RRF 融合", kb_id=1, top_k=5,
                                      dense_prefetch=10, sparse_prefetch=10, threshold=0.0)
    # 阈值 1.0：只允许"融合分满分"的强命中通过
    strict = await store.hybrid_search(query="Qdrant RRF 融合", kb_id=1, top_k=5,
                                       dense_prefetch=10, sparse_prefetch=10, threshold=1.0)
    assert len(strict) < len(loose), "提高阈值应过滤掉弱命中"
    assert all(h.score_breakdown["rrf"] >= 1.0 for h in strict)
    assert all("Qdrant" in h.text for h in strict)


async def test_kb_isolation_and_delete_document(store):
    await store.upsert_chunks([
        {"id": 1, "kb_id": 1, "document_id": 10, "seq": 0, "text": "知识库1的内容", "meta": {"file": "a.md"}},
        {"id": 2, "kb_id": 2, "document_id": 20, "seq": 0, "text": "知识库2的内容", "meta": {"file": "b.md"}},
    ])
    # 按 kb 过滤：查 kb=1 不该看到 kb=2 的内容
    hits = await store.hybrid_search(query="内容", kb_id=1, top_k=5,
                                     dense_prefetch=10, sparse_prefetch=10, threshold=0.0)
    assert all(h.kb_id == 1 for h in hits)

    # 删除 kb=1 的文档 10 后，再搜 kb=1 应为空
    await store.delete_document(doc_id=10, kb_id=1)
    hits = await store.hybrid_search(query="知识库1", kb_id=1, top_k=5,
                                     dense_prefetch=10, sparse_prefetch=10, threshold=0.0)
    assert hits == []
