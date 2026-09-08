"""LLM Gateway 测试：用"假 provider"验证 转发 / 降级 / 用量统计，全程不联网、不需要真 Key。

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
    ProviderError,
    ProviderRegistry,
    StreamUsage,
)


# ---------- 三个"假 provider" ----------

class FakeOK:
    async def stream(self, messages, model):
        yield StreamUsage(text="hi ")
        yield StreamUsage(text="there", out_tokens=5, hit_tokens=3, miss_tokens=10)


class FakeBoom:
    async def stream(self, messages, model):
        raise ProviderError("429 rate limit")   # 模拟主 provider 被限流
        yield  # 永远执行不到；但必须出现 yield，函数才是"异步生成器"才能被 async for 消费


class FakeFallback:
    async def stream(self, messages, model):
        yield StreamUsage(text="ok", out_tokens=3, miss_tokens=8)


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
        if u.out_tokens:
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
    assert usage.out_tokens == 5
    assert usage.hit_tokens == 3             # 输入 3 个命中缓存
    assert usage.miss_tokens == 10           # 10 个未命中 → 总输入 13


async def test_fallback_on_rate_limit():
    reg = make_registry(lambda: FakeBoom())
    text, usage, fb = await collect(ChatGateway(reg, gw_config(), keys={}))
    assert text == "ok"                      # 备胎答上了
    assert fb is True                        # 确实降级了
    assert usage.out_tokens == 3


async def test_unknown_provider_raises():
    reg = ProviderRegistry()
    with pytest.raises(ProviderError):
        reg.build("openai", api_key="")      # 没注册过的名字 → 报错
