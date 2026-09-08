"""LLM Gateway 测试：用"假 provider"验证 转发 / 降级 / 计费，全程不联网、不需要真 Key。

假 provider 就是实现了 async stream(messages, model) 接口的普通类：
- FakeOK：主 provider，正常返回文字 + 用量
- FakeBoom：主 provider，一调就抛"限流"错（模拟 429）
- FakeFallback：备胎 provider，能正常回答
"""
import pytest

from app.core.llm_gateway import (
    ChatGateway,
    ChatMessage,
    GatewayConfig,
    ModelPricing,
    ProviderError,
    ProviderRegistry,
    StreamUsage,
)


# ---------- 三个"假 provider" ----------

class FakeOK:
    async def stream(self, messages, model):
        yield StreamUsage(text="hi ")
        yield StreamUsage(text="there", usage_in=10, usage_out=5)


class FakeBoom:
    async def stream(self, messages, model):
        raise ProviderError("429 rate limit")   # 模拟主 provider 被限流
        yield  # 永远执行不到；但必须出现 yield，函数才是"异步生成器"才能被 async for 消费


class FakeFallback:
    async def stream(self, messages, model):
        yield StreamUsage(text="ok", usage_in=8, usage_out=3)


def make_registry(primary_factory):
    reg = ProviderRegistry()
    reg.register("anthropic", lambda key, base_url=None: primary_factory())
    reg.register("deepseek", lambda key, base_url=None: FakeFallback())
    return reg


def gw_config():
    return GatewayConfig(
        primary_provider="anthropic",
        primary_model="claude-x",
        fallback_provider="deepseek",
        fallback_model="deepseek-chat",
    )


async def collect(gateway):
    """把流式输出收成一段文字 + 用量 + 是否降级。"""
    text, usage, fallback = "", None, None
    async for u in gateway.stream([ChatMessage(role="user", content="q")]):
        text += u.text
        if u.usage_in:
            usage = u
        if u.fallback is not None:
            fallback = u.fallback
    return text, usage, fallback


# ---------- 测试 ----------

async def test_primary_success_no_fallback():
    reg = make_registry(lambda: FakeOK())
    text, usage, fb = await collect(ChatGateway(reg, gw_config(), keys={}))
    assert text == "hi there"
    assert fb is False                       # 没降级
    assert usage.usage_in == 10 and usage.usage_out == 5


async def test_fallback_on_rate_limit():
    reg = make_registry(lambda: FakeBoom())
    text, usage, fb = await collect(ChatGateway(reg, gw_config(), keys={}))
    assert text == "ok"                      # 备胎答上了
    assert fb is True                        # 确实降级了
    assert usage.usage_in == 8


async def test_unknown_provider_raises():
    reg = ProviderRegistry()
    with pytest.raises(ProviderError):
        reg.build("openai", api_key="")      # 没注册过的名字 → 报错


def test_model_pricing_by_prefix():
    # 单价（$/1M tokens）：claude-sonnet 输入 3 美元/百万、deepseek-chat 输出 1.1 美元/百万
    assert ModelPricing.cost("claude-sonnet-4-5", 1_000_000, 0) == 3.0
    assert ModelPricing.cost("deepseek-chat", 0, 1_000_000) == 1.1
    assert ModelPricing.cost("claude-opus-4-5", 0, 1_000_000) == 75.0
