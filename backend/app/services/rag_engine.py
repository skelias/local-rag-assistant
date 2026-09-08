"""RAG Engine —— 把 QdrantStore(查) + ChatGateway(答) + Config(参数) 串成流水线。

职责（对照第 12 课）：
1. retrieve()：按"单一参数源"检索 → 拼上下文 → 结构化 sources（按 tokens 预算裁剪）
2. generate_stream()：先把 sources 事件推给上层，再流式吐模型回答
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator

from app.core.llm_gateway import ChatMessage
from app.services.repositories import ConfigRepository

RAG_SYSTEM_PROMPT = (
    "你是本地 RAG 知识库助手。只能依据提供的[来源]内容回答；"
    "若来源不足，明确说'知识库中没有相关内容'，不要编造。"
    "回答中需要引用时用 [n] 标注对应来源编号。默认用中文回答（提问是其他语言则跟随）。"
)


# ---------- 检索参数：单一来源 ----------

@dataclass
class RetrievalParams:
    """一份完整的检索参数。默认值写在这，kb 配置可覆盖，请求级 override 最高。"""
    top_k: int = 20
    dense_prefetch: int = 30
    sparse_prefetch: int = 30
    threshold: float = 0.0
    rerank_enabled: bool = False
    max_source_tokens: int = 4000


class RetrievalParamsResolver:
    """参数解析器：user_config 的 kb.<id>.retrieval.* 是唯一权威，请求可显式覆盖。
    命中测试面板与对话检索都从这里读 —— 保证两边永远一致。"""

    # (参数名, 数据库键)
    _FIELDS = [
        ("top_k", "top_k"),
        ("dense_prefetch", "dense_prefetch"),
        ("sparse_prefetch", "sparse_prefetch"),
        ("threshold", "threshold"),
        ("rerank_enabled", "rerank_enabled"),
        ("max_source_tokens", "max_source_tokens"),
    ]

    def __init__(self, cfg: ConfigRepository, kb_id: int):
        self.cfg = cfg
        self.kb_id = kb_id

    async def resolve(self, overrides: dict | None = None) -> RetrievalParams:
        overrides = overrides or {}
        p = RetrievalParams()
        for attr, cfg_suffix in self._FIELDS:
            if attr in overrides and overrides[attr] is not None:
                setattr(p, attr, overrides[attr])
            else:
                val = await self.cfg.get(f"kb.{self.kb_id}.retrieval.{cfg_suffix}",
                                         getattr(p, attr))
                if val is not None:
                    setattr(p, attr, val)
        return p


# ---------- 来源（引用） ----------

@dataclass
class SourceRef:
    """一条可点击引用。前端点 [n] 就能拿到这些字段渲染来源面板。"""
    n: int                       # 引用编号（1 起）
    kb_id: int
    document_id: int
    chunk_id: int
    file: str
    page: int | None = None
    score: float = 0.0
    score_breakdown: dict = field(default_factory=dict)
    text: str = ""               # 片段摘要（引用抽屉里展示）
    seq: int = 0

    def to_dict(self) -> dict:
        return {
            "n": self.n, "kb_id": self.kb_id, "document_id": self.document_id,
            "chunk_id": self.chunk_id, "file": self.file, "page": self.page,
            "score": round(self.score, 4), "score_breakdown": self.score_breakdown,
            "text": self.text[:500], "seq": self.seq,
        }


def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数：中英文混合下约 4 字符 ≈ 1 token。"""
    return max(1, len(text) // 4)


# ---------- 引擎 ----------

class RAGEngine:
    def __init__(self, store, gateway, cfg: ConfigRepository, kb_id: int = 1):
        self.store = store          # 需有 hybrid_search(query,kb_id,top_k,dense_prefetch,sparse_prefetch,threshold)
        self.gateway = gateway      # 需有 stream(messages) -> AsyncIterator[StreamUsage]
        self.cfg = cfg
        self.kb_id = kb_id

    async def retrieve(self, query: str, kb_id: int | None = None,
                       overrides: dict | None = None) -> tuple[str, list[SourceRef]]:
        """查资料 → (上下文文本, 引用列表)。"""
        kb_id = kb_id or self.kb_id
        p = await RetrievalParamsResolver(self.cfg, kb_id).resolve(overrides)

        hits = await self.store.hybrid_search(
            query=query, kb_id=kb_id, top_k=p.top_k,
            dense_prefetch=p.dense_prefetch, sparse_prefetch=p.sparse_prefetch,
            threshold=p.threshold,
        )
        if p.rerank_enabled and hits:
            hits = await self._rerank(query, hits, p)

        sources: list[SourceRef] = []
        parts: list[str] = []
        budget = p.max_source_tokens
        for i, h in enumerate(hits, start=1):
            tok = _estimate_tokens(h.text)
            if budget - tok < 0 and sources:
                break                       # 预算不够了，后面更强的也没有 —— 停
            budget -= tok
            src = SourceRef(
                n=i, kb_id=kb_id, document_id=h.document_id, chunk_id=h.chunk_id,
                file=h.file, page=h.page, score=h.score_breakdown.get("rrf", 0.0),
                score_breakdown=h.score_breakdown, text=h.text, seq=h.seq,
            )
            sources.append(src)
            parts.append(f"[来源{i}: {h.file}]\n{h.text}")

        return "\n\n".join(parts), sources

    async def _rerank(self, query: str, hits, p: RetrievalParams):
        """可选本地 Reranker（FlagEmbedding）。默认关闭；开启时才 import（避免重型依赖）。"""
        try:
            from FlagEmbedding import FlagReranker
        except Exception:
            return hits
        reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=False)
        scores = reranker.compute_score([(query, h.text) for h in hits])
        if not isinstance(scores, list):
            scores = [scores]
        for h, s in zip(hits, scores):
            h.score_breakdown["rerank"] = round(float(s), 4)
        hits.sort(key=lambda h: h.score_breakdown.get("rerank", 0.0), reverse=True)
        return hits[: max(1, p.top_k)]

    async def generate_stream(
        self,
        query: str,
        history: list[ChatMessage] | None = None,
        kb_id: int | None = None,
        model: str | None = None,
        overrides: dict | None = None,
    ) -> AsyncIterator[tuple[str, list[SourceRef] | None]]:
        """完整流水线。产出约定：
        - 第一帧：( "", sources )   —— 先告诉上层"我用了哪些资料"
        - 之后每帧：( 文字片, None ) —— 流式回答
        """
        kb_id = kb_id or self.kb_id
        context, sources = await self.retrieve(query, kb_id=kb_id, overrides=overrides)

        if context:
            user_payload = f"知识库检索结果：\n\n{context}\n\n问题：{query}"
        else:
            user_payload = f"（知识库未检索到相关内容）\n\n问题：{query}"

        messages = [ChatMessage(role="system", content=RAG_SYSTEM_PROMPT)]
        if history:
            messages.extend(history[-6:])     # 只带最近 3 轮（含 user+assistant 两条/轮）
        messages.append(ChatMessage(role="user", content=user_payload))

        sent = False
        async for u in self.gateway.stream(messages):
            if not sent:
                sent = True
                yield "", sources             # 首个事件推来源
            if u.text:
                yield u.text, None
