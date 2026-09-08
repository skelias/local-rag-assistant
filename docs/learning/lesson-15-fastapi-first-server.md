# 第 15 课：FastAPI —— 第一个 Web 服务

## 概念

- HTTP 请求的一生：URL → 路由匹配 → 调函数 → return dict → JSON 响应
- FastAPI 三件套：路由装饰器 @app.get/post / 路径参数 {kb_id} / Pydantic 自动校验+文档(/docs)
- uvicorn：ASGI 服务器（把 FastAPI 应用"跑在端口上"）
- ASGITransport：测试里内存调用应用，不需要真端口

## 本次产出

- `app/api/app.py`：create_app() → FastAPI(title, CORS 放开) + GET /api/health
- `run.py`：启动入口（uvicorn 跑 app.api.app:app @ 127.0.0.1:8000）—— P0-1 欠的账，现在补上
- `tests/test_health_api.py`：health 200 + /docs 200（新增 2 测试）

## 里程碑

**第一次真实跑起 Web 服务**：
```
INFO: Uvicorn running on http://127.0.0.1:8000
GET /api/health HTTP/1.1 200 OK  →  {"status":"ok","version":"0.1.0"}
```

## 自己动手（强烈推荐做一次）

```powershell
cd "D:\RAG个人AI助手\backend"
.\venv\Scripts\python run.py
# 另开浏览器打开：
#   http://127.0.0.1:8000/api/health   （返回 JSON）
#   http://127.0.0.1:8000/docs         （FastAPI 免费送的交互文档！）
# 用完在终端按 Ctrl+C 停服务器
```

## 状态

34 passed；commit `feat(p0-7): fastapi app with health route, run.py entry`
