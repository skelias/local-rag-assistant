"""LLM 设置接口：列出/添加/删除 Provider（含用户自定义 OpenAI 兼容端点）。

自定义 provider 元信息存 user_config：
  llm.custom_providers  = [{"id","label","base_url"}]
  llm.<id>_api_key      = 密钥（覆盖 .env）
  llm.<id>_base_url     = 端点（覆盖默认）
"""
from fastapi import APIRouter, Body, Depends, HTTPException
import httpx

from app.api.deps import get_db
from app.core.config import settings
from app.core.llm_gateway import _usable_key
from app.services.repositories import ConfigRepository

router = APIRouter(prefix="/api/llm", tags=["llm"])

BUILTIN = {
    "anthropic": "Claude (Anthropic)",
    "deepseek": "DeepSeek",
    "glm": "智谱 GLM",
    "kimi": "Kimi",
    "openai": "OpenAI (GPT)",
}


def _builtin_base_url(pid: str) -> str | None:
    return getattr(settings, f"{pid}_base_url", None)


async def _providers(cfg: ConfigRepository) -> list[dict]:
    out = []
    for pid, label in BUILTIN.items():
        key = await cfg.get(f"llm.{pid}_api_key", getattr(settings, f"{pid}_api_key", ""))
        base = await cfg.get(f"llm.{pid}_base_url", _builtin_base_url(pid))
        models = await cfg.get(f"llm.{pid}_models", []) or []
        out.append({"id": pid, "label": label, "base_url": base,
                    "builtin": True, "configured": _usable_key(key), "models": models})
    for c in (await cfg.get("llm.custom_providers", []) or []):
        cid = c.get("id")
        key = await cfg.get(f"llm.{cid}_api_key", "")
        models = await cfg.get(f"llm.{cid}_models", []) or []
        out.append({"id": cid, "label": c.get("label", cid),
                    "base_url": c.get("base_url"), "builtin": False,
                    "configured": _usable_key(key), "models": models})
    return out


@router.get("/options")
async def llm_options(db=Depends(get_db)) -> dict:
    """返回：可选的 provider 清单 + 当前生效的模型配置。"""
    cfg = ConfigRepository(db)
    return {
        "providers": await _providers(cfg),
        "primary_provider": await cfg.get("llm.primary_provider", settings.default_chat_provider),
        "primary_model": await cfg.get("llm.primary_model", settings.default_chat_model),
        "fallback_provider": await cfg.get("llm.fallback_provider", settings.fallback_chat_provider),
        "fallback_model": await cfg.get("llm.fallback_model", settings.fallback_chat_model),
    }


@router.post("/provider")
async def upsert_provider(db=Depends(get_db),
                          payload: dict = Body(...)) -> dict:
    """添加/更新一个 provider（自定义 = 任意 OpenAI 兼容端点）。"""
    cfg = ConfigRepository(db)
    pid = str(payload.get("id", "")).strip()
    label = str(payload.get("label", "")).strip()
    base_url = str(payload.get("base_url", "") or "").strip()
    api_key = str(payload.get("api_key", "") or "").strip()

    if not pid or not all(ch.isalnum() or ch in "_-." for ch in pid):
        raise HTTPException(400, "id 仅支持字母/数字/_/-/.")
    if pid in BUILTIN:
        label = BUILTIN[pid]

    if api_key:
        await cfg.set(f"llm.{pid}_api_key", api_key)
    if base_url:
        await cfg.set(f"llm.{pid}_base_url", base_url)
    models = payload.get("models")
    if isinstance(models, list):
        await cfg.set(f"llm.{pid}_models", [str(m).strip() for m in models if str(m).strip()])

    if pid not in BUILTIN:
        custom = await cfg.get("llm.custom_providers", []) or []
        custom = [c for c in custom if c.get("id") != pid]
        custom.append({"id": pid, "label": label or pid, "base_url": base_url})
        await cfg.set("llm.custom_providers", custom)

    return {"ok": True, "id": pid}


@router.delete("/provider/{pid}")
async def delete_provider(pid: str, db=Depends(get_db)) -> dict:
    """删除自定义 provider（内置不可删）。"""
    if pid in BUILTIN:
        raise HTTPException(400, "内置 provider 不可删除")
    cfg = ConfigRepository(db)
    custom = [c for c in (await cfg.get("llm.custom_providers", []) or []) if c.get("id") != pid]
    await cfg.set("llm.custom_providers", custom)
    await cfg.delete(f"llm.{pid}_api_key")
    await cfg.delete(f"llm.{pid}_base_url")
    await cfg.delete(f"llm.{pid}_models")
    return {"ok": True}


@router.post("/discover")
async def discover_models(payload: dict = Body(...)) -> dict:
    """拉取某个 OpenAI 兼容端点的模型列表（GET {base_url}/models）。

    只用于"发现"，本次请求不落库、凭据不保存 —— 用户确认后才写入 provider 配置。
    """
    base_url = (payload.get("base_url") or "").strip()
    api_key = (payload.get("api_key") or "").strip()
    if not base_url:
        raise HTTPException(400, "需要 base_url")

    url = base_url.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(url, headers=headers)
            r.raise_for_status()
            data = r.json().get("data", [])
            ids = sorted({m.get("id") for m in data if isinstance(m, dict) and m.get("id")})
            return {"models": [{"id": i} for i in ids]}
    except Exception as e:
        raise HTTPException(502, f"拉取失败：{e}")
