"""依赖注入：路由函数"要啥声明啥"，组件单例都挂在 app.state 上。

测试注入假组件（临时 DB / Fake 向量库），生产由 lifespan 建真组件 —— 路由代码不用区分。
"""
from fastapi import HTTPException, Request


def _need(request: Request, name: str):
    value = getattr(request.app.state, name, None)
    if value is None:
        raise HTTPException(503, f"{name} 未就绪（生产模式会自动初始化；测试需注入）")
    return value


def get_db(request: Request):
    return _need(request, "db")


def get_vector_store(request: Request):
    return _need(request, "vector_store")


def get_upload_dir(request: Request):
    return _need(request, "upload_dir")


def get_chat_gateway(request: Request):
    return _need(request, "chat_gateway")


def get_media_dir(request: Request):
    """用户上传文件（背景/头像）的根目录。注入时用注入值，否则回落 data/media。"""
    value = getattr(request.app.state, "media_dir", None)
    if value is None:
        from app.core.config import settings

        return settings.DATA_DIR / "media"
    return value
