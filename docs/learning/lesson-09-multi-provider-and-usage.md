# 第 9 课：需求变更重构 + 多厂商 Provider

## 发生了什么

1. 用户需求变化：**不需要计费（金额）**，只要 **token 消耗 + 缓存命中率** → 我们做了一次真实重构；
2. 用户要求支持多家模型：**Claude / DeepSeek / GLM / Kimi / GPT**。

这正是真实开发的样子：需求会变，架构要经得起改。

## 重构清单（计费 → 用量统计）

| 地方 | 改了什么 |
|---|---|
| usage_records 表 | 删掉 cost 列 → 加 cache_hit_tokens / cache_miss_tokens（输出 output_tokens 保留） |
| UsageRepository | record(out_tokens, hit_tokens, miss_tokens)；summary 返回 次数/输出/命中/未命中/总输入/命中率 |
| StreamUsage | usage_in/out → out_tokens / hit_tokens / miss_tokens |
| llm_gateway | 删除 ModelPricing（价格表） |

**缓存命中率** = 命中缓存输入 token ÷ (命中 + 未命中)。
什么是"prompt 缓存"：你多次请求的系统提示/资料前缀相同，厂商在服务端缓存它，
命中的部分又快又便宜（Claude/DeepSeek 会报告命中/未命中数字；GPT 不报告 → 全算未命中）。

## 多厂商怎么接入的（回答"怎么增加 API"）

- **Anthropic**（Claude）：原生 SDK → `AnthropicProvider`
- **DeepSeek / OpenAI(GPT) / 智谱GLM / Kimi / 任何 OpenAI 兼容端点**：同一个 `OpenAICompatProvider`
  （只差 base_url + key + 模型名！）
- `build_default_registry(cfg)`：**看 .env 里填了哪个真 Key 就登记哪家**
- 关键函数 `_usable_key`：占位符（sk-xxxxx）不算真 Key，避免拿着假 Key 去调 API

加新家 = 在 .env 加 `XXX_API_KEY`（+ 可选 `XXX_BASE_URL`）→ registry 列表加一行 → 默认模型指向它。

## Key 安全（重要）

- **不要把 Key 发到聊天里**；只填进项目根 `.env`（已被 gitignore）
- 程序从 .env 读，任何地方不打印 Key（冒烟脚本只打印回复与 token 统计）

## 新增文件

- `backend/scripts/smoke_llm.py`：真冒烟脚本（需要你在 .env 填真 Key）

## 状态

15 passed；commit `2f122d9`。P0-3 只剩"用真 Key 冒烟验证"。
