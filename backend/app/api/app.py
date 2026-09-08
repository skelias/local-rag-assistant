"""FastAPI 应用入口 —— "对外窗口"。

生命周期（lifespan）：
- 生产（python run.py）：启动时自动建真组件（Database/QdrantStore），关闭时回收；
- 测试：注入假组件（临时 DB / Fake 向量库 / 临时上传目录），不走 lifespan。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import knowledge
from app.core.config import settings


def create_app(db=None, vector_store=None, upload_dir=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # ---- 启动：缺啥补啥（真组件） ----
        if app.state.db is None:
            from app.models.database import Database

            _db = Database(settings.DB_PATH)
            await _db.init()
            app.state.db = _db
            app.state._own_db = True

        if app.state.vector_store is None:
            from app.core.embedding import BGEM3Provider
            from app.core.vector_store import QdrantStore

            embedder = BGEM3Provider()          # 懒加载：真正调用时才需要 torch
            vs = QdrantStore(
                settings.QDRANT_PATH, settings.qdrant_collection,
                settings.qdrant_vector_size, embedder,
            )
            await vs.init()
            app.state.vector_store = vs
            app.state._own_store = True

        if app.state.upload_dir is None:
            app.state.upload_dir = settings.UPLOAD_DIR

        yield

        # ---- 关闭：回收自己创建的 ----
        if getattr(app.state, "_own_store", False):
            await app.state.vector_store.close()
        if getattr(app.state, "_own_db", False):
            await app.state.db.close()

    app = FastAPI(
        title="RAG AI 助手",
        description="本地 RAG 知识库 + AI 助手（教学进行中…）",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 单例组件：注入的先用注入的；None 则等 lifespan 补
    app.state.db = db
    app.state.vector_store = vector_store
    app.state.upload_dir = upload_dir

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(knowledge.router)

    @app.get("/api/health")
    async def health():
        """健康检查：判断后端活着没。"""
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
