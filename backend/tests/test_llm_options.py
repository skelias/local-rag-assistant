"""/api/llm 测试：provider 增删查 + 自定义端点被网关登记。"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.app import create_app
from app.core.llm_gateway import build_gateway_from_config
from app.models.database import Database
from app.services.repositories import ConfigRepository


@pytest.fixture
async def client(tmp_path):
    db = Database(tmp_path / "l.db")
    await db.init()
    app = create_app(db=db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c, db
    await db.close()


async def test_options_lists_builtin_providers(client):
    c, _ = client
    r = await c.get("/api/llm/options")
    assert r.status_code == 200
    body = r.json()
    assert len(body["providers"]) >= 5
    assert any(p["id"] == "deepseek" for p in body["providers"])


async def test_upsert_custom_provider_and_delete(client):
    c, db = client
    up = await c.post("/api/llm/provider", json={
        "id": "my_openai", "label": "我的 OpenAI", "base_url": "https://api.example.com/v1",
        "api_key": "sk-real-key-123",
    })
    assert up.status_code == 200

    opts = (await c.get("/api/llm/options")).json()
    mine = [p for p in opts["providers"] if p["id"] == "my_openai"]
    assert mine and mine[0]["configured"] is True

    # 网关能登记这个自定义 provider
    gw = await build_gateway_from_config(ConfigRepository(db))
    assert "my_openai" in gw.registry._factories

    d = await c.delete("/api/llm/provider/my_openai")
    assert d.status_code == 200
    opts2 = (await c.get("/api/llm/options")).json()
    assert all(p["id"] != "my_openai" for p in opts2["providers"])


async def test_delete_builtin_rejected(client):
    c, _ = client
    r = await c.delete("/api/llm/provider/deepseek")
    assert r.status_code == 400
