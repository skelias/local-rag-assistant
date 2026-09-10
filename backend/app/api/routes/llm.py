"""LLM 选项接口：列出可选的 Provider 与当前生效的模型配置（供设置页渲染）。"""
from fastapi import APIRouter, Depends

from app.api.deps import get_db
from app.core.config import settings
from app.core.llm_gateway import _usable_key
from app.services.repositories import ConfigRepository

router = APIRouter(prefix="/api/llm", tags=["llm"])

PROVIDER_LABELS = {
    "anthropic": "Claude (Anthropic)",
    "deepseek": "DeepSeek",
    "glm": "智谱 GLM",
    "kimi": "Kimi",
    "openai": "OpenAI (GPT)",
}


@router.get("/options")
async def llm_options(db=Depends(get_db)) -> dict:
    """返回：可选的 provider 清单（含"是否已配置 Key"）+ 当前生效的模型配置。"""
    cfg = ConfigRepository(db)

    providers = []
    for pid, label in PROVIDER_LABELS.items():
        key = await cfg.get(f"llm.{pid}_api_key", getattr(settings, f"{pid}_api_key", ""))
        providers.append({"id": pid, "label": label, "configured": _usable_key(key)})

    return {
        "providers": providers,
        "primary_provider": await cfg.get("llm.primary_provider", settings.default_chat_provider),
        "primary_model": await cfg.get("llm.primary_model", settings.default_chat_model),
        "fallback_provider": await cfg.get("llm.fallback_provider", settings.fallback_chat_provider),
        "fallback_model": await cfg.get("llm.fallback_model", settings.fallback_chat_model),
    }
