# 第 17 课：SSE 流式对话 + 命中测试 + 配置路由（P0-7 收官）

## SSE 流式（chat.py）

SSE = Server-Sent Events：服务器"持续吐事件"，浏览器逐个收。
协议（前端以后照这个解析）：
```
event: sources   data: [{n,file,score,...}]   ① 先推来源（引用面板先画）
event: token     data: {"t":"一个字"}         ② 流式文字（一条条蹦）
event: done      data: {"conversation_id":N}  ③ 结束
```
chat 端点做的事：建/续会话 → 取最近 3 轮历史 → 存用户问题 → 引擎流式生成 → 完整回答+sources 落库 → done。

## 命中测试（knowledge.py 追加）

`POST /api/knowledge/{kb}/hit-test`：调 engine.retrieve，返回 {params, hits}。
与对话共用 RetrievalParamsResolver —— 单一参数源落地。

## 配置路由（config.py）

GET /api/config（倒全部设置）；PUT /api/config（写一条，运行生效）。
键名就是引擎/网关读的那些（kb.1.retrieval.top_k、llm.primary_model…）。

## 接线

- deps 加 get_chat_gateway；app 支持注入 chat_gateway，lifespan 里按 settings 建真网关（含已填 Key 的厂商）
- schemas 补 ChatRequest / HitTestRequest / ConfigItem

## 测试（4 个新增，合计 43 passed）

SSE 事件齐全(sources/token/done) / 对话持久化(user+assistant+sources) / 命中测试带 params+hits+score_breakdown / 配置 PUT→GET。

## 作业

```powershell
cd "D:\RAG个人AI助手\backend"; .\venv\Scripts\python -m pytest   # 43 passed
```
VS Code 看 chat.py 的 event_gen —— SSE 事件流长什么样。

## 注意（下一个里程碑）

现在 `run.py` 的对话/命中测试在**真跑**前还差一样东西：检索要调 embedder，
生产 embedder 是 BGE-M3（torch 没装）→ 会报"需要安装 FlagEmbedding + torch"。
所以下一课 = **装真实嵌入(数 GB 下载) + 真端到端验收**（上传→确认→真问 DeepSeek），P0-8 收官。
