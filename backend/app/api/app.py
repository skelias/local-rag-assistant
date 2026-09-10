"""FastAPI 应用入口 —— "对外窗口"。

生命周期（lifespan）：
- 生产（python run.py）：启动时自动建真组件（Database/QdrantStore），关闭时回收；
- 测试：注入假组件（临时 DB / Fake 向量库 / 临时上传目录），不走 lifespan。
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes import chat, config, knowledge, llm, profile
from app.core.config import settings


def _mount_frontend(app: FastAPI) -> None:
    """若 frontend/dist 已构建，将其作为 SPA 静态资源挂载到根路径。
    API 路由 (/api/*) 先注册先匹配，静态资源不会覆盖它们。"""
    dist = settings.DATA_DIR.parent / "frontend" / "dist"
    if not dist.is_dir():
        return

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        target = dist / full_path
        if full_path and target.is_file():
            return FileResponse(str(target))
        return FileResponse(str(dist / "index.html"))


def create_app(db=None, vector_store=None, upload_dir=None, chat_gateway=None,
               media_dir=None) -> FastAPI:
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

        # 注意：chat_gateway 不做静态单例 —— 每次请求由 deps 按数据库配置动态构建，
        # 这样设置页改"模型/Provider/Key"无需重启即生效（测试仍可注入静态假网关）。

        yield

        # ---- 关闭：回收自己创建的 ----
        if getattr(app.state, "_own_store", False):
            await app.state.vector_store.close()
        if getattr(app.state, "_own_db", False):
            await app.state.db.close()

    app = FastAPI(
        title="RAG AI 助手",
        description="本地 RAG 知识库 + AI 助手",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 单例组件：注入的先用注入的；None 则等 lifespan 补
    app.state.db = db
    app.state.vector_store = vector_store
    app.state.upload_dir = upload_dir
    app.state.chat_gateway = chat_gateway
    app.state.media_dir = media_dir

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(knowledge.router)
    app.include_router(chat.router)
    app.include_router(config.router)
    app.include_router(profile.router)
    app.include_router(llm.router)

    @app.get("/api/health")
    async def health():
        """健康检查：判断后端活着没。"""
        return {"status": "ok", "version": "0.1.0"}

    # ---- /media 静态托管（背景/头像等用户上传文件） ----
    media_root = Path(media_dir) if media_dir else settings.DATA_DIR / "media"
    media_root.mkdir(parents=True, exist_ok=True)
    app.state.media_dir = str(media_root)
    app.mount("/media", StaticFiles(directory=str(media_root)), name="media")

    # ---- 单端口静态托管（frontend/dist 存在时挂载） ----
    _mount_frontend(app)

    return app


app = create_app()
