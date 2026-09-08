# 第 11 课：Embedding 抽象 + Qdrant 混合检索(RRF)

## 概念速记

| 词 | 一句话 |
|---|---|
| Embedding | 文字 → 一串数字（向量）；语义相近 → 向量相近 |
| 稠密向量 dense | 密集数字串，抓"整体语义"（BGE-M3 = 1024 维） |
| 稀疏向量 sparse | 大面积为 0、关键词位置有值 → 精确命中（代码/编号/型号） |
| 向量数据库 | 存向量、找最接近向量的数据库（Qdrant 本地文件模式） |
| Collection/Point/Payload | 向量表 / 一行(一个分块) / 附带的元数据(原文等) |
| 命名向量 | 一个点同时存 dense 和 sparse 两路 |
| RRF 融合 | 两路检索结果按排名合并 → 取长补短 |

为什么双通道：语义问题靠 dense；"errno 10053""模型名"这类精确词靠 sparse/BM25。

## 本次写的东西

- `app/core/embedding.py`：`EmbeddingProvider`（ABC：encode_dense/encode_sparse）
  + `BGEM3Provider`（本地 BGE-M3，**用到才 import** FlagEmbedding → 没装 torch 也不报错）
- `app/core/vector_store.py`：`QdrantStore`
  - init：本地文件模式建 collection，注册 dense+sparse 两路命名向量
  - upsert_chunks：向量化 → 写入（payload 带 kb_id/document_id/seq/text/file…）
  - hybrid_search：双路 prefetch → FusionQuery(RRF) → 阈值过滤 → SearchHit(带 score_breakdown)
  - delete_document：按 (document_id, kb_id) 删
- `tests/test_vector_store.py`：FakeEmbedder（确定性假向量）3 个测试

## 踩的坑 / 学到的经验

1. **库的 API 会变**：qdrant-client 1.19 把 `PrefetchQuery` 改成了 `Prefetch`（且顶层过滤参数叫 `query_filter`）。
   读报错 `cannot import name 'PrefetchQuery'` 后，正确姿势是**去查它到底叫什么**（dir/签名/introspection），而不是硬猜。
2. **单候选点 RRF=1.0**：只有一个点时融合分=1.0（归一化），阈值 1.0 滤不掉 —— 测试假设错了，改成"多候选、强 vs 弱"的真实场景。

## 状态

- 测试 **18 passed**（health2 + database2 + repositories8 + gateway3 + vector_store3）
- commit `feat(p0-4): embedding ABC + BGE-M3 lazy provider + qdrant hybrid RRF store`
- P0-4 未完：真实嵌入（torch/FlagEmbedding，几个 GB）在"端到端能真跑"那课前再装；
  未装期间：测试用 FakeEmbedder，接口一致。

## 命令速记

```powershell
cd "D:\RAG个人AI助手\backend"
.\venv\Scripts\python -m pytest     # 18 passed
```
