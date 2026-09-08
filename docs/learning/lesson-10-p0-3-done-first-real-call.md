# 第 10 课：P0-3 收官 —— 第一次真实调用 + 模型名纪律

## 实测结果（2026-09，DeepSeek）

你的账号 `/models` 实测可用：
- `deepseek-v4-flash`（默认，日常用）
- `deepseek-v4-flash-vision-exp`（视觉实验版）
- `deepseek-v4-pro`（更强/贵）

**纪律（用户要求，以后不再犯）**：
1. 模型名**绝不凭记忆写**，写之前用 `scripts/list_models.py` 实测；
2. 官方名会随版本退役/改名（`deepseek-chat` 别名已于 2026-07-24 停用）；
3. 新厂商接入，先跑 list_models 确认再写进配置/文档。

## 冒烟结果（第一次真调用）

两轮调用共享一段约 880 token 的长前缀：
- 第 1 轮：命中 0 / 未命中 880 → 命中率 0%（首次建缓存）
- 第 2 轮：命中 768 / 未命中 112 → 命中率 87.3%（相同前缀命中缓存）

这就是"缓存命中率"的现实意义：RAG 每次提问都带同一段系统提示/知识上下文，前缀被厂商缓存后，后续调用又快又省。

## 密钥处理血的教训（本次排障）

1. 用户贴 Key 常见错误：**把真 Key 追加在示例占位符后面**（没删 `sk-xxxxx…`）→ 修复=整行替换；
2. 我误把"占位符后的中文注释"当成"追加的真 Key"，还自动"修复"改坏了文件 → **教训：自动改配置前先确认语义，宁慢勿错**；已恢复干净模板重来；
3. 验证 Key 的正确姿势：**只看长度/是否含 xxxxx/开头，绝不打印 Key**；再用 list_models 实测（Key 无效会 401）。

## P0-3 收官

- LLM Gateway：provider 注册表 + 降级 + 流式 + 用量(token+缓存命中率)
- 真实 provider：anthropic 原生；deepseek/openai/glm/kimi 走 OpenAI 兼容
- 脚本：`list_models.py`（问账号可用模型）、`smoke_llm.py`（真调用冒烟）
- 测试 15 passed；15 测试 = health(2) + database(2) + repositories(8) + gateway(3)
- commit：`4588ea5` + 本轮冒烟升级
