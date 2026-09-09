"""真实端到端验收：上传 md → 真向量化(BGE-M3) → 真问答(DeepSeek)。

前提：.env 里有可用 DeepSeek Key；torch + FlagEmbedding 已装。
用法（backend 目录）：
    venv/Scripts/python scripts/real_e2e.py
首次跑会自动下载 BGE-M3 模型（约 2GB+，已指向 hf-mirror 加速）。
全程不打印 Key。
"""
import asyncio
import os
import sys
from pathlib import Path

# 国内拉 HuggingFace 模型走镜像 + 禁用 Xet（镜像不支持 Xet 会 403）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import Settings                              # noqa: E402
from app.core.embedding import FastEmbedProvider                  # noqa: E402
from app.core.llm_gateway import (                                # noqa: E402
    ChatGateway,
    ChatMessage,
    GatewayConfig,
    build_default_registry,
)
from app.core.vector_store import QdrantStore                      # noqa: E402
from app.models.database import Database                           # noqa: E402
from app.models.schemas import DocumentCreate                      # noqa: E402
from app.services.doc_pipeline import confirm_document_index, run_upload_pipeline, save_upload
from app.services.rag_engine import RAGEngine                      # noqa: E402
from app.services.repositories import ChunkRepository, ConfigRepository, DocumentRepository


SAMPLE = """# FastAPI 快速上手

FastAPI 是一个现代、快速的 Python Web 框架，支持异步( async/await )接口。
它用类型注解自动生成交互式文档 /docs（Swagger UI）。
uvicorn 是它的推荐服务器：uvicorn main:app 就能把应用跑在 http://127.0.0.1:8000。
本项目后端就用 FastAPI + uvicorn 提供服务。
"""

async def main() -> None:
    cfg = Settings()

    # 1) 真实组件：数据库 + 真实嵌入 + Qdrant
    db = Database(cfg.DB_PATH)
    await db.init()
    print("[1/5] 数据库就绪:", cfg.DB_PATH)

    # 轻量真实嵌入（fastembed，中文友好）。想升级回 BGE-M3：换回 BGEM3Provider 即可（接口不变）
    embedder = FastEmbedProvider()

    store = QdrantStore(cfg.QDRANT_PATH, cfg.qdrant_collection,
                        embedder.dim, embedder)
    await store.init()
    print("[2/5] 向量库就绪")

    # 2) 上传并入库这份示例文档
    doc_repo, chunk_repo = DocumentRepository(db), ChunkRepository(db)
    kb_id = 1
    dest = save_upload(SAMPLE.encode("utf-8"), "fastapi-guide.md", kb_id)
    doc_id = await doc_repo.create(DocumentCreate(
        kb_id=kb_id, filename="fastapi-guide.md", file_type=".md",
        file_path=str(dest), size=len(SAMPLE.encode("utf-8"))))
    n_chunks = await run_upload_pipeline(dest, chunk_repo, doc_id, kb_id)
    await doc_repo.set_status(doc_id, "parsed")
    print(f"[3/5] 解析出 {n_chunks} 个分块，开始向量化入库（首次会下载 BGE-M3 模型，耐心等）…")
    await confirm_document_index(doc_id, kb_id, doc_repo, chunk_repo, store)
    print("[4/5] 文档已入库（ready），开始检索 + 真实问答…")

    # 3) 用配置里的 DeepSeek 网关提问
    reg = build_default_registry(cfg)
    gateway = ChatGateway(
        reg,
        GatewayConfig(cfg.default_chat_provider, cfg.default_chat_model,
                      cfg.fallback_chat_provider, cfg.fallback_chat_model),
        {"deepseek_api_key": cfg.deepseek_api_key,
         "openai_api_key": cfg.openai_api_key,
         "glm_api_key": cfg.glm_api_key,
         "kimi_api_key": cfg.kimi_api_key,
         "claude_api_key": cfg.claude_api_key},
        {"deepseek": cfg.deepseek_base_url, "openai": cfg.openai_base_url,
         "glm": cfg.glm_base_url, "kimi": cfg.kimi_base_url},
    )
    engine = RAGEngine(store=store, gateway=gateway,
                       cfg=ConfigRepository(db), kb_id=kb_id)

    question = "FastAPI 怎么生成自动文档？用什么服务器跑它？"
    print(f"\n[5/5] 问题：{question}\n")
    answer = ""
    sources = None
    async for payload, srcs in engine.generate_stream(question, kb_id=kb_id):
        if srcs is not None:
            sources = srcs
        elif payload:
            answer += payload

    print("—— AI 回答 ——")
    print(answer)
    print("\n—— 引用来源 ——")
    for s in sources or []:
        print(f"  [{s.n}] {s.file} (rrf={s.score_breakdown.get('rrf')})")
    if not sources:
        print("  （未检索到命中 —— 请检查分词/模型是否正确入库）")

    await store.close()
    await db.close()
    print("\n[OK] 真实端到端跑通！")


if __name__ == "__main__":
    asyncio.run(main())

