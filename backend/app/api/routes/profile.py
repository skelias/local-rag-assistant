"""个人化资源接口：背景 / 头像 上传与管理。

契约见 docs/designs/spec-addendum-01 §2.3（方案 B：存 data/media，写 user_config，/media 静态托管）。
键：ui.background / ui.avatar_user / ui.avatar_ai（值是 /media/... URL 路径）
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_db, get_media_dir
from app.services.repositories import ConfigRepository

router = APIRouter(prefix="/api/profile", tags=["profile"])

KIND_DIR = {
    "background": "backgrounds",
    "avatar_user": "avatars",
    "avatar_ai": "avatars",
}
KIND_KEY = {
    "background": "ui.background",
    "avatar_user": "ui.avatar_user",
    "avatar_ai": "ui.avatar_ai",
}
KIND_FIELD = {
    "ui.background": "background",
    "ui.avatar_user": "avatar_user",
    "ui.avatar_ai": "avatar_ai",
}
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp"}
MAX_BYTES = 2 * 1024 * 1024  # 2MB


@router.get("")
async def get_profile(db=Depends(get_db)) -> dict:
    """返回当前配置：{background, avatar_user, avatar_ai}（null 或 /media/... URL）。"""
    cfg = ConfigRepository(db)
    return {KIND_FIELD[k]: await cfg.get(k) for k in KIND_KEY.values()}


@router.post("/upload")
async def upload_profile_file(
    kind: str,
    file: UploadFile = File(...),
    db=Depends(get_db),
    media_dir=Depends(get_media_dir),
) -> dict:
    """上传一张图片（background / avatar_user / avatar_ai）→ 存盘 + 写配置 → 返回 URL。"""
    if kind not in KIND_DIR:
        raise HTTPException(400, f"kind 必须是 {sorted(KIND_DIR)} 之一")

    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "图片不能超过 2MB")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(415, "仅支持 png / jpg / jpeg / webp")

    folder = Path(media_dir) / KIND_DIR[kind]
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (folder / name).write_bytes(data)

    url = f"/media/{KIND_DIR[kind]}/{name}"
    cfg = ConfigRepository(db)
    await cfg.set(KIND_KEY[kind], url)
    return {"url": url}
