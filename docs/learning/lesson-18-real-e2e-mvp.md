# 第 18 课：真实端到端 MVP（P0-8 收官）

## 结果（真实运行 scripts/real_e2e.py）

问：「FastAPI 怎么生成自动文档？用什么服务器跑它？」
答：「FastAPI 通过类型注解自动生成交互式文档 /docs（Swagger UI）[1]，推荐使用 uvicorn 作为服务器……[1]」
引用：[1] fastapi-guide.md (rrf=1.0) [2] … (rrf=0.667)

**真实检索 → 真实向量化 → 真实 DeepSeek 生成 → 带引用回答。MVP 达成。**

## 这一路踩的坑（都是真实世界的课）

1. HuggingFace 官方不可达（国内超时）→ hf-mirror 通，但：
2. hf-mirror 对走 **Xet 协议**的文件 403 → 修：`HF_HUB_DISABLE_XET=1`
3. 即使如此，**BGE-M3（2.3GB）在 mirror/ModelScope 都下载停滞**
   → 决策：MVP 先用**轻量 fastembed**（bge-small-zh ~90MB + BM25 稀疏），BGE-M3 留作网络好时的升级
4. Qdrant 本地存储**被残留进程锁住** → 先清进程再跑
5. print ✅ emoji 在 GBK 控制台崩溃 → 脚本输出别用 emoji（或设 UTF-8）

## 架构为什么经得起这次"换模型"

我们一开始就把 Embedding 抽成接口（EmbeddingProvider）+ 向量维度以 embedder.dim 为准：
换 BGE-M3 ⇄ fastembed **只改一行实例化**，Store/Engine/API 全不动 —— 抽象的价值兑现了。

## 现状

- 真实嵌入：FastEmbedProvider（稠密 bge-small-zh 512 维 + 稀疏 Qdrant/bm25），模型自动下载到 hf 缓存
- 真实对话：DeepSeek（.env 的 key / deepseek-v4-flash）
- 脚本：scripts/real_e2e.py（一键验收）、scripts/download_bge_m3.py（将来下 BGE-M3）
- requirements 已与事实同步（fastembed 进运行时；BGE-M3/torch 保留为可选注释）

## P0-8 收官 → 后端 MVP 完成

P0-1~P0-8 全部 ✅：脚手架/数据层/LLM 网关/向量检索/RAG 引擎/文档管线/FastAPI+SSE/端到端。
43 个自动化测试保持全绿。
下一步只剩前端（P0-9~P0-12）—— 按用户约定，前端动手前先商量设计。
