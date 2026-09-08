"""Qdrant 向量存储（本地文件模式，免 Docker）。

核心概念（对照第 11 课讲解）：
- collection：一张"向量表"（这里一张：rag_documents）
- Point：一行 = 一个分块；自带 payload（原文、文档 id 等元数据）
- 命名向量：一个点同时存 dense（稠密）与 sparse（稀疏）两路向量
- 混合检索：两路各召回 top N → RRF 融合出最终排名 → 阈值过滤
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    PointStruct,
    Prefetch,
    SparseIndexParams,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from app.core.embedding import EmbeddingProvider


@dataclass
class SearchHit:
    """一条命中结果（检索层返回给上层的数据形状）。"""
    chunk_id: int
    document_id: int
    kb_id: int
    seq: int
    text: str
    meta: dict = field(default_factory=dict)
    score_breakdown: dict[str, float] = field(default_factory=dict)  # {rrf, vector?, bm25?}

    @property
    def file(self) -> str:
        return self.meta.get("file", "")

    @property
    def page(self):
        return self.meta.get("page")


def _sparse(sp: dict[int, float]) -> SparseVector:
    """把 {token_id: 权重} 转成 Qdrant SparseVector（indices 需升序）。"""
    ids = sorted(sp.keys())
    return SparseVector(indices=ids, values=[sp[i] for i in ids])


class QdrantStore:
    """向量表的管理者：建表 / 写入 / 混合检索 / 按文档删除。"""

    def __init__(self, path: Path | str, collection: str,
                 vector_size: int, embedder: EmbeddingProvider):
        self.path = Path(path)
        self.collection = collection
        self.vector_size = vector_size
        self.embedder = embedder
        self._client: AsyncQdrantClient | None = None

    async def init(self) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        self._client = AsyncQdrantClient(path=str(self.path))   # 本地文件模式
        existing = await self._client.get_collections()
        if self.collection not in {c.name for c in existing.collections}:
            await self._client.create_collection(
                collection_name=self.collection,
                vectors_config={
                    "dense": VectorParams(size=self.vector_size, distance=Distance.COSINE),
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=True)),
                },
            )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    # ---------- 写入 ----------

    async def upsert_chunks(self, chunks: list[dict]) -> None:
        """把分块（含 text + meta）向量化后写入集合。chunks 元素需含 id/kb_id/document_id/seq/text/meta。"""
        enc = await self.embedder.encode([c["text"] for c in chunks], sparse=True)
        dense_list, sparse_list = enc["dense"], enc["sparse"]

        points = []
        for c, d, s in zip(chunks, dense_list, sparse_list):
            points.append(PointStruct(
                id=c["id"],
                vector={
                    "dense": d,
                    "sparse": _sparse(s),
                },
                payload={"kb_id": c["kb_id"], "document_id": c["document_id"],
                         "seq": c["seq"], "text": c["text"], **c["meta"]},
            ))
        await self._client.upsert(collection_name=self.collection, points=points)

    # ---------- 删除 ----------

    async def delete_document(self, doc_id: int, kb_id: int) -> None:
        """按 (文档, 知识库) 删除它的全部向量点。"""
        await self._client.delete(
            collection_name=self.collection,
            points_selector=Filter(must=[
                FieldCondition(key="document_id", match=MatchValue(value=doc_id)),
                FieldCondition(key="kb_id", match=MatchValue(value=kb_id)),
            ]),
        )

    # ---------- 检索 ----------

    async def hybrid_search(self, query: str, kb_id: int, top_k: int,
                            dense_prefetch: int, sparse_prefetch: int,
                            threshold: float) -> list[SearchHit]:
        """双通道召回 + RRF 融合。

        返回的 score_breakdown：rrf = 融合分（必给）；vector/bm25 = 各路原始分（该路命中才给）。
        """
        enc = await self.embedder.encode([query], sparse=True)
        dvec = enc["dense"][0]
        svec = _sparse(enc["sparse"][0])

        kb_filter = Filter(must=[FieldCondition(key="kb_id", match=MatchValue(value=kb_id))])

        resp = await self._client.query_points(
            collection_name=self.collection,
            prefetch=[
                Prefetch(query=dvec, using="dense", limit=dense_prefetch, filter=kb_filter),
                Prefetch(query=svec, using="sparse", limit=sparse_prefetch, filter=kb_filter),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )

        # 逐路原始分（用于展示"这分来自稠密还是稀疏"）
        dense_hits = await self._query_single(dvec, "dense", kb_id, kb_filter, dense_prefetch)
        sparse_hits = await self._query_single(svec, "sparse", kb_id, kb_filter, sparse_prefetch)
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
            if breakdown["rrf"] < threshold:
                continue
            out.append(SearchHit(
                chunk_id=int(p.id),
                kb_id=payload.get("kb_id", kb_id),
                document_id=payload.get("document_id", 0),
                seq=payload.get("seq", 0),
                text=payload.get("text", ""),
                meta=payload,
                score_breakdown=breakdown,
            ))
        return out

    async def _query_single(self, query, using: str, kb_id: int, kb_filter: Filter,
                            limit: int):
        """单路召回，返回该路 top 命中的原始分。"""
        resp = await self._client.query_points(
            collection_name=self.collection,
            query=query, using=using, limit=limit, query_filter=kb_filter,
        )
        return resp.points
