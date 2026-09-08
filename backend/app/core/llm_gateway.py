"""LLM Gateway —— 统一模型调用层（"总机"）。

谁想调模型（RAG 生成 / Agent 推理），都走这里；它负责：
1. 按配置选 provider（anthropic / deepseek / glm / kimi / openai）+ 模型名；
2. 流式转发（一个字一个字往外送）；
3. 主 provider 报错/限流时，自动降级到备胎（fallback）；
4. 汇报用量：输出 token 与"缓存命中/未命中"输入 token（不计费，只统计）。

设计要点：
- 模型名与 provider 由"配置"决定，代码不写死任何具体模型；
- provider 以"注册表"方式登记：名字 → 工厂函数（给 key/base_url，返回一个能 stream 的对象）；
- 测试用假 provider 即可验证逻辑，无需真 Key / 联网。
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
    """流式输出的"一小片"：要么是文字(text)，要么是结尾的用量(token 数)。
    用量字段：
    - out_tokens   输出 token
    - hit_tokens   输入中"命中缓存"的 token（Claude/DeepSeek 会报告）
    - miss_tokens  输入中"未命中缓存"的 token
    输入总 token = hit + miss；缓存命中率 = hit / (hit + miss)。
    fallback：None=正常主路；False/True 见 ChatGateway 里赋值。"""
    text: str = ""
    out_tokens: int = 0
    hit_tokens: int = 0
    miss_tokens: int = 0
    fallback: bool | None = None


@dataclass
class GatewayConfig:
    """网关配置：主力 + 备胎 各是什么 provider / 模型。"""
    primary_provider: str
    primary_model: str
    fallback_provider: str | None = None
    fallback_model: str | None = None


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


# ---------- 真实 Provider（薄封装官方 SDK） ----------

class AnthropicProvider:
    """Anthropic(Claude) 原生接口。

    用量换算（Anthropic 语义）：
    - miss = input_tokens(新输入) + cache_creation_input_tokens(新写入缓存的)
    - hit  = cache_read_input_tokens(直接命中缓存读到的)
    """

    def __init__(self, api_key: str):
        from anthropic import AsyncAnthropic
        self._client = AsyncAnthropic(api_key=api_key)

    async def stream(self, messages: list[ChatMessage], model: str) -> AsyncIterator[StreamUsage]:
        try:
            async with self._client.messages.stream(
                model=model,
                max_tokens=4096,
                messages=[{"role": m.role, "content": m.content} for m in messages],
            ) as stream:
                async for text in stream.text_stream:
                    yield StreamUsage(text=text)
                u = (await stream.get_final_message()).usage
                miss = (getattr(u, "input_tokens", 0) or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0)
                hit = getattr(u, "cache_read_input_tokens", 0) or 0
                yield StreamUsage(out_tokens=getattr(u, "output_tokens", 0) or 0,
                                  hit_tokens=hit, miss_tokens=miss)
        except Exception as e:      # 429 / 超时 / 网络 统一视为可重试错误 → 可降级
            raise ProviderError(f"anthropic: {e}") from e


class OpenAICompatProvider:
    """一切 OpenAI 兼容端点：DeepSeek / OpenAI(GPT) / 智谱GLM / Kimi / 本地 Ollama…

    用量换算（DeepSeek 报告 prompt_cache_hit/miss；GPT 不报缓存 → 全算 miss）。
    """

    def __init__(self, api_key: str, base_url: str | None = None):
        from openai import AsyncOpenAI
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)

    async def stream(self, messages: list[ChatMessage], model: str) -> AsyncIterator[StreamUsage]:
        try:
            stream = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                stream=True,
                stream_options={"include_usage": True},   # 让结尾带上 usage
            )
            async for chunk in stream:
                if chunk.usage:                            # 结尾的用量块
                    u = chunk.usage
                    hit = getattr(u, "prompt_cache_hit_tokens", 0) or 0
                    miss = getattr(u, "prompt_cache_miss_tokens", None)
                    if miss is None:                       # GPT 不报缓存 → 全部算 miss
                        miss = u.prompt_tokens or 0
                    yield StreamUsage(out_tokens=u.completion_tokens or 0,
                                      hit_tokens=hit, miss_tokens=miss)
                    continue
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield StreamUsage(text=delta.content)
        except Exception as e:
            raise ProviderError(f"openai_compat: {e}") from e


# ---------- 注册工厂：看配置里有哪些 Key，就把哪些 provider 登记上 ----------

def _usable_key(key: str) -> bool:
    """判断 Key 是否"真的可用"：非空 且 不是占位符(sk-xxxx…)。"""
    return bool(key) and "xxxxx" not in key.lower()


def build_default_registry(cfg) -> ProviderRegistry:
    """根据配置(哪些 Key 填了)登记 provider。
    约定：provider 名字 = 读 key/base_url 的后缀，
    例如名字 "glm" → cfg.glm_api_key / cfg.glm_base_url。"""
    reg = ProviderRegistry()

    if _usable_key(cfg.claude_api_key):
        reg.register("anthropic", lambda key, base_url=None: AnthropicProvider(key))

    compat = [
        ("deepseek", cfg.deepseek_api_key, cfg.deepseek_base_url),
        ("openai", cfg.openai_api_key, cfg.openai_base_url),
        ("glm", cfg.glm_api_key, cfg.glm_base_url),
        ("kimi", cfg.kimi_api_key, cfg.kimi_base_url),
    ]
    for name, key, base_url in compat:
        if _usable_key(key):  # 只登记"填了真 Key"的厂商
            reg.register(name, lambda key, base_url=base_url: OpenAICompatProvider(key, base_url))

    return reg
