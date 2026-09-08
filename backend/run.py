"""启动入口：python run.py 即可起服务（开发期）。

教学说明：P0-1 计划里本文件一直等到"能真正启动服务器"这课才建 —— 现在到了。
reload=False 便于教学演示；开发久了可改 True（改代码自动重启）。
"""
import uvicorn

from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
