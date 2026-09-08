"""Embedding（向量化）抽象与实现。

为什么要"抽象"（抽象类 ABC）？
- 上层（Qdrant 存储、RAG 引擎）只需要知道"给一段文字 → 给我稠密+稀疏向量"；
- 至于底层是本地 BGE-M3、还是未来换成 API embedding，上层不用改。
测试里注入一个 FakeEmbedder 即可，完全不碰真实模型。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


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
