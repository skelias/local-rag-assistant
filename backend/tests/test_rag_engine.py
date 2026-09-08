"""RAG Engine 测试：检索参数解析 + 上下文/sources 组装 + 流式产出。

全程假组件：假 store（返回固定命中）、假 gateway（回一句"答案"）、假 config（内存字典）。
"""
import pytest

from app.core.llm_gateway import ChatMessage
from app.core.vector_store import SearchHit
from app.services.rag_engine import RAGEngine, RetrievalParamsResolver, SourceRef


class _FakeStore:
    """假装是 QdrantStore，固定返回两条命中。"""
    async def hybrid_search(self, query, kb_id, top_k, dense_prefetch, sparse_prefetch, threshold):
        return [
            SearchHit(chunk_id=1, document_id=10, kb_id=kb_id, seq=0,
                      text="Qdrant 用 RRF 融合两路召回" * 4,
                      meta={"file": "qdrant.md"},
                      score_breakdown={"rrf": 0.8, "vector": 0.9, "bm25": 0.5}),
            SearchHit(chunk_id=2, document_id=11, kb_id=kb_id, seq=1,
                      text="B" * 400,
                      meta={"file": "other.md", "page": 3},
                      score_breakdown={"rrf": 0.6, "vector": 0.7}),
        ]


class _FakeGateway:
    async def stream(self, messages):
        for m in messages:
            if m.role == "user":
                yield type("U", (), {"text": "基于来源回答。", "out_tokens": 9,
                                     "hit_tokens": 0, "miss_tokens": 3, "fallback": False})()


class _CfgRepo:
    def __init__(self, data: dict | None = None):
        self.data = data or {}

    async def get(self, key, default=None):
        return self.data.get(key, default)


# ---------- 检索参数：单一来源 ----------

async def test_params_resolver_defaults():
    p = await RetrievalParamsResolver(_CfgRepo({}), kb_id=1).resolve(overrides={})
    assert p.top_k == 20 and p.threshold == 0.0 and p.rerank_enabled is False


async def test_params_resolver_kb_config_then_override():
    repo = _CfgRepo({"kb.1.retrieval.top_k": 6, "kb.1.retrieval.threshold": 0.5})
    # 没显式覆盖 → 用数据库里的 kb 配置
    p = await RetrievalParamsResolver(repo, kb_id=1).resolve(overrides={})
    assert p.top_k == 6 and p.threshold == 0.5
    # 请求里显式覆盖 top_k → 覆盖生效，其余仍用 kb 配置
    p2 = await RetrievalParamsResolver(repo, kb_id=1).resolve(overrides={"top_k": 9})
    assert p2.top_k == 9 and p2.threshold == 0.5


# ---------- 检索 → 上下文 + 来源 ----------

async def test_retrieve_builds_sources_and_context():
    engine = RAGEngine(store=_FakeStore(), gateway=_FakeGateway(), cfg=_CfgRepo({}))
    context, sources = await engine.retrieve("Qdrant RRF", kb_id=1, overrides={})

    assert len(sources) == 2
    assert sources[0].file == "qdrant.md"
    assert sources[1].page == 3
    assert sources[0].n == 1 and sources[1].n == 2          # 引用编号从 1 开始
    assert sources[0].score_breakdown["rrf"] == 0.8
    assert "Qdrant" in context                               # 上下文里真的带了资料
    assert "[来源1: qdrant.md]" in context


async def test_retrieve_token_budget_cuts_tail():
    """第二条来源太大、超过预算 → 被裁掉，只保留强相关的第一条。"""
    class HugeStore(_FakeStore):
        async def hybrid_search(self, query, kb_id, top_k, dense_prefetch, sparse_prefetch, threshold):
            return [
                SearchHit(chunk_id=1, document_id=10, kb_id=kb_id, seq=0,
                          text="A" * 100, meta={"file": "first.md"},
                          score_breakdown={"rrf": 0.9}),
                SearchHit(chunk_id=2, document_id=11, kb_id=kb_id, seq=1,
                          text="B" * 30000, meta={"file": "huge2.md"},
                          score_breakdown={"rrf": 0.5}),
            ]

    # 预算只有 50 token：第一条 100 字符≈25 token 放得下，第二条 30000 字符≈7500 放不下
    cfg = _CfgRepo({"kb.1.retrieval.max_source_tokens": 50})
    engine = RAGEngine(store=HugeStore(), gateway=_FakeGateway(), cfg=cfg)

    context, sources = await engine.retrieve("q", kb_id=1, overrides={})
    assert len(sources) == 1
    assert sources[0].file == "first.md"          # 只留下强的
    assert "huge2.md" not in [s.file for s in sources]


# ---------- 流式生成：先给来源，再吐文字 ----------

async def test_generate_stream_emits_sources_then_text():
    engine = RAGEngine(store=_FakeStore(), gateway=_FakeGateway(), cfg=_CfgRepo({}))
    got_sources, text = None, ""
    async for payload, sources in engine.generate_stream("Qdrant 怎么融合", kb_id=1):
        if sources is not None:
            got_sources = sources
        elif payload:
            text += payload
    assert got_sources is not None and len(got_sources) == 2
    assert text == "基于来源回答。"
