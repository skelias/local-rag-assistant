# 第 12 课：RAG Engine —— 组装流水线

## RAGEngine 是"组装层"

把三样零件串起来：QdrantStore(查) + ChatGateway(答) + ConfigRepository(参数)。
流程：检索 → 拼上下文 →（可选 rerank）→ tokens 预算裁剪 → 流式生成 + 结构化 sources。

## 两个设计要点

1. **单一参数源**：`RetrievalParamsResolver` 只从 `kb.<id>.retrieval.*`（user_config）读，
   命中测试面板与对话检索共用它；请求级 override 只在显式给时才生效。
   优先级：请求 override > kb 配置 > 代码默认值。

2. **按 tokens 裁来源**：来源按相关度从高到低逐个加入，`budget - tok < 0` 就停（至少保 1 条）。
   估算：`len//4` 字符≈token。

## 产出协议（generate_stream）

- 第一帧：`("", sources)` —— 先告诉前端"用了哪些资料"（渲染引用面板）
- 后续帧：`(文字片, None)` —— 流式回答

## SourceRef（可点击引用）

字段：n/kb_id/document_id/chunk_id/file/page/score/score_breakdown/text/seq；
`to_dict()` 给 API/前端用。

## 测试（5 个，合计 23 passed）

- 参数解析：默认值 / kb 配置优先 / 请求 override 覆盖
- retrieve：两条命中 → sources 带 file/page/编号/分数；上下文含 `[来源1: file]`
- 预算裁尾：第二条 30000 字符超过预算 → 被裁掉
- generate_stream：先发 sources 事件，再吐文字

## 状态

commit `feat(p0-5): rag engine ...`
进度：P0-5 引擎与参数源完成（HTTP 接线在 P0-7）。

## 思考题（答案见下）

Q：为什么"先发 sources 事件、再流式吐文字"对前端体验重要？
<details>
<summary>A</summary>
前端可以先渲染"引用/来源抽屉"（有内容在加载的反馈），并且即使用户在回答中途就点开来源看原文，也不会等整段回答结束 —— 体验上更接近"查完资料正在写"，而不是"憋着等结果"。
</details>
