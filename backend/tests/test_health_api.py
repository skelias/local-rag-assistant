"""第一个 Web 接口测试：/api/health。

技巧：httpx.ASGITransport —— 在"内存里"调用 FastAPI 应用，不需要真的开端口，
测试又快又稳（真正的服务器留给手动冒烟）。
"""
from httpx import ASGITransport, AsyncClient

from app.api.app import create_app


async def test_health_returns_ok():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_docs_page_available():
    """FastAPI 自动生成的交互文档页（以后对接口就靠它）。"""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        r = await client.get("/docs")
    assert r.status_code == 200
