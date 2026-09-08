# 第 16 课：依赖注入 + 知识库上传/预览/确认路由

## 概念

- 依赖注入 DI：单例挂在 app.state，路由用 Depends 声明"我要啥"，FastAPI 自动给
  → 测试注入假组件、生产 lifespan 建真组件，路由代码不分真假
- lifespan（生命周期）：uvicorn 启动时执行 → 建真组件；关闭时回收（asynccontextmanager）
- UploadFile：FastAPI 接收 multipart 文件流；`await file.read()` 取字节

## 新增文件/改动

- `app/api/deps.py`：get_db / get_vector_store / get_upload_dir（缺组件 → 503 友好报错）
- `app/api/routes/knowledge.py`：5 个端点
  | 方法 | 路径 | 作用 |
  |---|---|---|
  | POST | /api/knowledge/{kb}/documents | 上传→解析→parsed（415 类型/413 大小/422 解析失败） |
  | GET | /api/knowledge/{kb}/documents | 文档列表（含状态与已索引数） |
  | GET | .../documents/{id}/preview | 分段预览（只读） |
  | POST | .../documents/{id}/confirm | 确认入库 → ready（幂等；真嵌入未装 → 422 提示） |
  | DELETE | .../documents/{id} | 删向量+级联删 chunks+删原文件 |
- `app.py`：create_app(db=, vector_store=, upload_dir=) 可注入；lifespan 缺啥补啥；
  挂载 knowledge 路由；测试注入 → 不走 lifespan
- config.py：加 max_upload_mb / allowed_exts
- repositories：DocumentRepository.delete（补漏，测试抓出来的）

## 测试（5 个新增，合计 39 passed）

上传 parsed+pending 数 / 415 拒绝 / 预览返回 chunks / 确认→ready+chunk_count / 删除后列表为空。

## 作业（浏览器玩一次）

```powershell
cd "D:\RAG个人AI助手\backend"; .\venv\Scripts\python run.py
```
浏览器开 `http://127.0.0.1:8000/docs` → 找 `POST /api/knowledge/1/documents` → Try it out →
上传一个本地 .md 文件 → Execute，看返回 `"status": "parsed"` 和 pending_chunks。
再点开 `GET .../documents/{doc_id}/preview` 用刚才的 id 试 —— 能看到你的文档被切成哪些块！
（confirm 现在会 422 报"需要真实嵌入"，属预期 —— 下一步就装真嵌入。）
