"""FastAPI 应用入口 —— "对外窗口"。

当前：最小可用版（健康检查 + 自动文档）。
后续课逐步加：数据库/向量库注入（lifespan）、上传/chat/配置路由。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG AI 助手",
        description="本地 RAG 知识库 + AI 助手（教学进行中…）",
        version="0.1.0",
    )

    # 跨域：开发期前端(5173)要访问后端(8000)，先放开；发布期收紧
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        """健康检查：判断后端活着没。"""
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
