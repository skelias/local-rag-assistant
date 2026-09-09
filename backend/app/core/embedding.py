"""Embedding（向量化）抽象与实现。

为什么要"抽象"（抽象类 ABC）？
- 上层（Qdrant 存储、RAG 引擎）只需要知道"给一段文字 → 给我稠密+稀疏向量"；
- 至于底层是本地 BGE-M3、还是未来换成 API embedding，上层不用改。
测试里注入一个 FakeEmbedder 即可，完全不碰真实模型。
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

# 国内访问 HuggingFace 模型仓库的通用设置（走镜像 + 禁 Xet，Xet 在镜像上会 403）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


class EmbeddingProvider(ABC):
    """向量化服务接口。dim = 稠密向量维度。"""

    dim: int = 1024

    @abstractmethod
    async def encode_dense(self, texts: list[str]) -> list[list[float]]:
        """稠密向量：一段文字 → 一串浮点数（语义相似度靠它算）。"""

    @abstractmethod
    async def encode_sparse(self, texts: list[str]) -> list[dict[int, float]]:
        """稀疏向量：一段文字 → {token_id: 权重}（精确关键词命中靠它算）。"""

    async def encode(self, texts: list[str], sparse: bool = True) -> dict[str, Any]:
        """一次调用同时拿两路（或只拿稠密）。返回 {"dense": [...], "sparse": [...]}。"""
        dense = await self.encode_dense(texts)
        if not sparse:
            return {"dense": dense}
        return {"dense": dense, "sparse": await self.encode_sparse(texts)}


class BGEM3Provider(EmbeddingProvider):
    """本地 BGE-M3（FlagEmbedding）。一次编码同时给稠密 + 稀疏(词法权重)。

    注意：FlagEmbedding 依赖 torch，体积大（数 GB）。
    本类采用"用到才 import"的写法 —— 没装 torch 时导入本模块也不报错，
    真正调用 encode 才会提示装依赖。CPU 也能跑，只是偏慢。
    """

    def __init__(self, model_name: str = "BAAI/bge-m3", use_fp16: bool = False):
        self.model_name = model_name
        self.use_fp16 = use_fp16
        self._model = None
        self.dim = 1024

    def _load(self):
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel
            except ImportError as e:  # 教学期：torch/FlagEmbedding 未装时的友好提示
                raise RuntimeError(
                    "BGEM3Provider 需要 FlagEmbedding + torch。安装："
                    "venv/Scripts/python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple "
                    "FlagEmbedding torch --index-url https://download.pytorch.org/whl/cpu"
                ) from e
            self._model = BGEM3FlagModel(self.model_name, use_fp16=self.use_fp16)
        return self._model

    async def encode_dense(self, texts: list[str]) -> list[list[float]]:
        import asyncio
        model = self._load()
        out = await asyncio.to_thread(
            lambda: model.encode(texts, return_dense=True, return_sparse=False,
                                 return_colbert_vecs=False)["dense_vecs"].tolist()
        )
        return out

    async def encode_sparse(self, texts: list[str]) -> list[dict[int, float]]:
        import asyncio
        model = self._load()
        out = await asyncio.to_thread(
            lambda: model.encode(texts, return_dense=False, return_sparse=True,
                                 return_colbert_vecs=False)["lexical_weights"]
        )
        return [{int(k): float(v) for k, v in weights.items()} for weights in out]


class FastEmbedProvider(EmbeddingProvider):
    """轻量真实嵌入（ONNX，无 torch）：稠密 bge-small-zh + 稀疏 BM25。

    - 稠密：BAAI/bge-small-zh-v1.5（约 90MB，中文友好，512 维）
    - 稀疏：Qdrant/bm25（精确关键词命中）
    首次 encode 会自动下载模型（走上面设置的 hf-mirror）。
    之后网络允许时，可把 main_provider 换回 BGE-M3 —— 上层接口不变。
    """

    dim = 512  # bge-small-zh-v1.5 稠密维度

    def __init__(self, dense_model: str = "BAAI/bge-small-zh-v1.5",
                 sparse_model: str = "Qdrant/bm25"):
        self.dense_model = dense_model
        self.sparse_model = sparse_model
        self._dense = None
        self._sparse = None

    def _load_dense(self):
        if self._dense is None:
            try:
                from fastembed import TextEmbedding
            except ImportError as e:
                raise RuntimeError("FastEmbedProvider 需要 fastembed：pip install fastembed") from e
            self._dense = TextEmbedding(self.dense_model)
        return self._dense

    def _load_sparse(self):
        if self._sparse is None:
            try:
                from fastembed import SparseTextEmbedding
            except ImportError as e:
                raise RuntimeError("FastEmbedProvider 需要 fastembed：pip install fastembed") from e
            self._sparse = SparseTextEmbedding(self.sparse_model)
        return self._sparse

    async def encode_dense(self, texts: list[str]) -> list[list[float]]:
        import asyncio
        model = self._load_dense()
        vectors = await asyncio.to_thread(lambda: list(model.embed(texts)))
        return [v.tolist() for v in vectors]

    async def encode_sparse(self, texts: list[str]) -> list[dict[int, float]]:
        import asyncio
        model = self._load_sparse()
        embeddings = await asyncio.to_thread(lambda: list(model.embed(texts)))
        result = []
        for e in embeddings:
            result.append({int(idx): float(val)
                           for idx, val in zip(e.indices.tolist(), e.values.tolist())})
        return result
