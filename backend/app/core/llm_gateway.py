"""LLM Gateway —— 统一模型调用层（"总机"）。

谁想调模型（RAG 生成 / Agent 推理），都走这里；它负责：
1. 按配置选 provider（anthropic / deepseek / openai_compat）+ 模型名；
2. 流式转发（一个字一个字往外送）；
3. 主 provider 报错/限流时，自动降级到备胎（fallback）；
4. 用量/计费交给上层记账（ModelPricing 提供单价表）。

设计要点：
- 模型名与 provider 由"配置"决定，代码不写死任何具体模型；
- provider 以"注册表"方式登记：名字 → 工厂函数（给 key/base_url，返回一个能 stream 的对象）；
- 测试用假 provider 即可验证逻辑，无需真 Key / 联网。

真实 SDK 薄封装（Anthropic / OpenAI 兼容）在下一课加入本文件。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Callable


# ---------- 数据结构 ----------

@dataclass
class ChatMessage:
    """一条对话消息：谁说的 + 内容。"""
    role: str        # user / assistant / system
    content: str


@dataclass
class StreamUsage:
    """流式输出的"一小片"：要么是文字(text)，要么是结尾的用量(usage_*)。
    fallback：None=正常主路；False/True 见 ChatGateway 里赋值。"""
    text: str = ""
    usage_in: int = 0
    usage_out: int = 0
    fallback: bool | None = None


@dataclass
class GatewayConfig:
    """网关配置：主力 + 备胎 各是什么 provider / 模型。"""
    primary_provider: str
    primary_model: str
    fallback_provider: str | None = None
    fallback_model: str | None = None


# ---------- 计费 ----------

class ModelPricing:
    """按模型名前缀匹配单价（美元 / 1M tokens）。
    表里没有的用兜底价；以后可让用户配置覆盖。"""

    _TABLE: dict[str, tuple[float, float]] = {
        "claude-opus": (15.0, 75.0),
        "claude-sonnet": (3.0, 15.0),
        "claude-": (3.0, 15.0),
        "deepseek-chat": (0.27, 1.1),
        "deepseek-reasoner": (0.55, 2.19),
        "gpt-": (2.5, 10.0),
    }
    _DEFAULT = (1.0, 2.0)

    @classmethod
    def cost(cls, model: str, in_tokens: int, out_tokens: int) -> float:
        """算钱：输入token数/100万 × 输入单价 + 输出token数/100万 × 输出单价。"""
        pin, pout = cls._DEFAULT
        for prefix, (i, o) in cls._TABLE.items():
            if model.startswith(prefix):
                pin, pout = i, o
                break
        return (in_tokens / 1_000_000) * pin + (out_tokens / 1_000_000) * pout


# ---------- 错误 ----------

class ProviderError(Exception):
    """provider 出错。retryable=True 表示"值得试试备胎"（限流/超时等）。"""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


# ---------- 注册表 ----------

class ProviderRegistry:
    """provider 登记处：名字 → 工厂函数。

    工厂函数签名：factory(api_key: str, base_url: str | None) -> 一个会 stream 的对象。
    """

    def __init__(self):
        self._factories: dict[str, Callable[[str, str | None], object]] = {}

    def register(self, name: str, factory: Callable[[str, str | None], object]) -> None:
        self._factories[name] = factory

    def build(self, name: str, api_key: str, base_url: str | None = None):
        """按名字造出一个 provider 实例；没登记过 → ProviderError。"""
        if name not in self._factories:
            raise ProviderError(f"unknown provider: {name}", retryable=False)
        return self._factories[name](api_key, base_url)


# ---------- 网关（降级逻辑核心） ----------

class ChatGateway:
    """总机：用主 provider 流式回答；主 provider 报 ProviderError 且有备胎时无缝切换。"""

    def __init__(self, registry: ProviderRegistry, config: GatewayConfig,
                 keys: dict[str, str], base_urls: dict[str, str | None] | None = None):
        self.registry = registry
        self.config = config
        self.keys = keys                    # {"claude_api_key": "...", "deepseek_api_key": "..."}
        self.base_urls = base_urls or {}

    def _provider(self, name: str):
        """根据 provider 名字找 key、造实例。
        约定：key 的读取规则 = 优先 <name>_api_key，没有就用 claude_api_key。"""
        key = self.keys.get(f"{name}_api_key") or self.keys.get("claude_api_key") or ""
        return self.registry.build(name, key, self.base_urls.get(name))

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[StreamUsage]:
        """核心逻辑：先走主路；万一主路抛 ProviderError，改走备胎。"""
        provider = self._provider(self.config.primary_provider)
        try:
            async for u in provider.stream(messages, self.config.primary_model):
                u.fallback = False           # 标记：这是主路的输出
                yield u
            return                            # 主路顺利走完，函数结束
        except ProviderError:
            # 主路挂了 —— 有备胎就切，没有就原样抛给上层
            if not self.config.fallback_provider:
                raise

        fallback = self._provider(self.config.fallback_provider)
        async for u in fallback.stream(messages, self.config.fallback_model):
            u.fallback = True                # 标记：这是降级后的输出
            yield u
