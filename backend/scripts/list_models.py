"""查询某家兼容厂商账号下"可用模型清单"（免得凭印象猜模型名）。

用法（在 backend 目录）：
   venv/Scripts/python scripts/list_models.py [provider]

provider 默认 deepseek，可选 openai / glm / kimi（需对应 Key 已填入项目根 .env）。
原理：OpenAI 兼容接口都有 GET /models —— 返回你这个账号能用的模型列表。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 让 import app.* 生效

from app.core.config import Settings                              # noqa: E402
from app.core.llm_gateway import _usable_key                      # noqa: E402


async def main() -> None:
    provider = sys.argv[1] if len(sys.argv) > 1 else "deepseek"
    cfg = Settings()
    key = getattr(cfg, f"{provider}_api_key", "")
    base = getattr(cfg, f"{provider}_base_url", None)

    if not _usable_key(key):
        print(f"⚠️  {provider} 的 Key 没填或还是占位符 —— 先编辑项目根 .env")
        return

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=key, base_url=base)
    try:
        resp = await client.models.list()
        ids = sorted(m.id for m in resp.data)
        print(f"{provider} 账号可用模型：")
        for mid in ids:
            print("  -", mid)
    except Exception as e:
        print("查询失败（Key 无效 / 网络 / base_url 不对？）：", e)


if __name__ == "__main__":
    asyncio.run(main())
