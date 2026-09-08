# 第 8 课：LLM Gateway 核心（注册表 + 降级 + 计费）

## 概念速记

| 词 | 一句话 | 比喻 |
|---|---|---|
| HTTP | 程序上网说话的通用协议（请求/响应 + URL + 方法 + 状态码） | 点外卖 |
| API | 服务商公布的"点餐窗口/格式" | 菜单+窗口 |
| API Key | 证明你身份的令牌 = 钱 | 钥匙 |
| 流式 stream | AI 想到一个字就吐一个字，不憋大招 | 水龙头 |
| provider | 模型厂商（anthropic / deepseek / openai 兼容端点） | 供应商 |

## Gateway 四职责

选 provider/模型 → 流式转发 → 主挂了降备胎 → 记账（用量/费用）

## 本次写的文件

`backend/app/core/llm_gateway.py`：
- 数据类：ChatMessage / StreamUsage(text,usage_in,usage_out,fallback) / GatewayConfig
- ModelPricing：按模型名前缀查单价（$ / 1M tokens）→ `cost(model,in,out)`
- ProviderError(retryable)：provider 出错的信号
- ProviderRegistry：名字→工厂函数，build(name,key,base_url)
- ChatGateway.stream：try 主路 → 抛 ProviderError 且配了 fallback → 切备胎；每个输出片标记 fallback True/False

## 今天踩的坑：async 生成器 vs 协程

`async def f(): raise ... `（函数体**没有 yield**）= 普通协程 → 不能 `async for`。
只有函数体里**出现 yield** 的 async def 才是"异步生成器"，才能被 `async for` 消费。
修法：在故意抛错的假 provider 里加一个永远到不了的 `yield`。

## 测试

`tests/test_llm_gateway.py`：3 个假 provider（OK/Boom/Fallback）验证 主路成功、429 降级、未知 provider 报错、按前缀算钱。
全量 **16 passed**。

## 状态

commit `feat(p0-3): llm gateway core - registry, fallback, pricing`
进度：P0-3 进行中（还差：真实 SDK 薄封装 + 从配置读 Key + 记账接线）

## 命令速记

```powershell
cd "D:\RAG个人AI助手\backend"
.\venv\Scripts\python -m pytest
```
