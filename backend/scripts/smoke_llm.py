"""真实冒烟脚本：真的调用一次模型，验证 Key/模型/网络/降级链路。

用法：
1. 在项目根 .env 里填好 Key（DEEPSEEK_API_KEY 等）并设好 DEFAULT_CHAT_PROVIDER/MODEL；
2. 运行（在 backend 目录）：
   venv/Scripts/python scripts/smoke_llm.py

注意：脚本只打印回复与 token/缓存统计，绝不打印 Key。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 让 import app.* 生效

from app.core.config import Settings                              # noqa: E402
from app.core.llm_gateway import (                                # noqa: E402
    ChatGateway,
    ChatMessage,
    GatewayConfig,
    build_default_registry,
)


async def main() -> None:
    cfg = Settings()
    reg = build_default_registry(cfg)

    keys = {
        "claude_api_key": cfg.claude_api_key,
        "deepseek_api_key": cfg.deepseek_api_key,
        "openai_api_key": cfg.openai_api_key,
        "glm_api_key": cfg.glm_api_key,
        "kimi_api_key": cfg.kimi_api_key,
    }
    base_urls = {
        "deepseek": cfg.deepseek_base_url,
        "openai": cfg.openai_base_url,
        "glm": cfg.glm_base_url,
        "kimi": cfg.kimi_base_url,
    }
    gw_cfg = GatewayConfig(
        primary_provider=cfg.default_chat_provider,
        primary_model=cfg.default_chat_model,
        fallback_provider=cfg.fallback_chat_provider,
        fallback_model=cfg.fallback_chat_model,
    )

    print(f"主力 = {gw_cfg.primary_provider}/{gw_cfg.primary_model}")
    print(f"备胎 = {gw_cfg.fallback_provider}/{gw_cfg.fallback_model}")
    print("已登记的 provider：", sorted(reg._factories.keys()))
    if not reg._factories:
        print("[注意]  没有填任何 Key —— 请先编辑项目根 .env")
        return

    gate = ChatGateway(reg, gw_cfg, keys, base_urls)

    # 共享长前缀：第二轮会命中 DeepSeek 的自动 prompt 缓存 → 演示"缓存命中率"
    prefix = "【知识库背景】" + (
        "FastAPI 是一个现代 Python Web 框架；RAG 指检索增强生成：先建索引再召回再生成。\n" * 30
    )

    print("\n=== 真实调用（连打两轮，演示缓存命中率） ===")
    for rnd in (1, 2):
        text, usage, used_fallback = "", None, None
        async for u in gate.stream([
            ChatMessage(role="system", content=prefix),
            ChatMessage(role="user", content=f"请只回复：第 {rnd} 次调用成功。"),
        ]):
            if u.text:
                text += u.text
            if u.out_tokens:
                usage = u
            if u.fallback is not None:
                used_fallback = u.fallback

        print(f"\n第 {rnd} 次回复：{text.strip()}")
        if usage:
            total_in = usage.hit_tokens + usage.miss_tokens
            rate = usage.hit_tokens / total_in if total_in else 0.0
            print(f"  输出 {usage.out_tokens} token | "
                  f"输入 命中缓存 {usage.hit_tokens} / 未命中 {usage.miss_tokens} "
                  f"| 缓存命中率 {rate:.1%}")
        print("  降级：", "是（用了备胎）" if used_fallback else "否")


if __name__ == "__main__":
    asyncio.run(main())

