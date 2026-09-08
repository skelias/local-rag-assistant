# 第 14 课：文档管线（下）—— 上传 → 预览 → 确认入库（P0-6 收官）

## 完整流程（为什么"预览"和"确认"要分开）

上传 → ①save_upload 落盘 → ②登记 documents(uploading)
     → ③run_upload_pipeline 解析+分块写 SQLite(pending)；文档置 parsed(待确认)
     → ④preview 只读看分段（前端）→ ⑤confirm 写向量库 + indexed + 文档 ready

②与⑤分开 = 对标 MaxKB"入库前人工校正"：分块切得烂就在确认前删掉重传，垃圾不进向量库。

## 本次新增（doc_pipeline.py 末尾）

- `save_upload(content, filename, kb_id, base_dir=None)`：落盘到 data/uploads/kb{id}/，base_dir 测试可注入
- `run_upload_pipeline(path, chunk_repo, doc_id, kb_id)`：解析→分块→insert_many(pending)，返回块数
- `confirm_document_index(doc_id, kb_id, doc_repo, chunk_repo, store)`：写向量库→indexed→ready

## 测试（4 个新增，合计 32 passed）

落盘路径/内容 / md 分块 pending 带 file meta / 代码按行批切带 lang meta / 确认后 store 收到同批块且 indexed、文档 ready。
测试技巧：用 RecordingStore（记录收到的块）代替真 Qdrant —— 专注验证编排逻辑。

## 状态

- commit `feat(p0-6): upload save, parse-split pipeline, preview/confirm index flow`
- P0-6 完成（HTTP 上传端点接线在 P0-7）
- 进度：P0-1~P0-6 后端 6/8 ✅

## 思考题

Q：为什么 confirm 里要先 `delete_by_document`（在 run_upload_pipeline 开头）？
A：同一文档可能被重新上传/重解析 —— 不先清旧块，旧的 pending/已索引块会和新的混在一起，造成重复检索。
