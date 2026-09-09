"""/api/profile 测试：背景与头像的上传/读取 + 静态文件真实可访问。"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.app import create_app
from app.models.database import Database


@pytest.fixture
async def ctx(tmp_path):
    db = Database(tmp_path / "p.db")
    await db.init()
    app = create_app(db=db, media_dir=tmp_path / "media")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c, tmp_path
    await db.close()


async def _png_bytes() -> bytes:
    return bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c6360000002000100" "05fe02fe0000000049454e44ae426082")


async def test_upload_background_and_read(ctx):
    client, tmp = ctx
    r = await client.post("/api/profile/upload", params={"kind": "background"},
                          files={"file": ("bg.png", await _png_bytes(), "image/png")})
    assert r.status_code == 200, r.text
    url = r.json()["url"]
    assert url.startswith("/media/backgrounds/")

    # 文件真的落到 media/backgrounds/
    name = url.rsplit("/", 1)[1]
    assert (tmp / "media" / "backgrounds" / name).exists()

    # GET 能读回
    g = await client.get("/api/profile")
    body = g.json()
    assert body["background"] == url
    assert body["avatar_user"] is None

    # 静态托管真实可访问
    img = await client.get(url)
    assert img.status_code == 200
    assert img.content[:8] == b"\x89PNG\r\n\x1a\n"


async def test_upload_avatar_user_and_ai(ctx):
    client, _ = ctx
    for kind in ("avatar_user", "avatar_ai"):
        r = await client.post("/api/profile/upload", params={"kind": kind},
                              files={"file": (f"{kind}.jpg", b"jpegdata", "image/jpeg")})
        assert r.status_code == 200, r.text
    body = (await client.get("/api/profile")).json()
    assert body["avatar_user"].startswith("/media/avatars/")
    assert body["avatar_ai"].startswith("/media/avatars/")


async def test_reject_bad_kind_and_ext(ctx):
    client, _ = ctx
    bad = await client.post("/api/profile/upload", params={"kind": "wallpaper"},
                            files={"file": ("x.png", b"data", "image/png")})
    assert bad.status_code == 400

    ext = await client.post("/api/profile/upload", params={"kind": "background"},
                            files={"file": ("x.gif", b"GIF89a", "image/gif")})
    assert ext.status_code == 415
