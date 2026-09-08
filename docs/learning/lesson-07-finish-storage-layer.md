# 第 7 课：Chunk / Config / Usage Repository → P0-2 收官

## 本次新增的三个"管理员"

| Repository | 管的表 | 方法 |
|---|---|---|
| ChunkRepository | chunks | delete_by_document / insert_many / list_pending / list_all / mark_indexed |
| ConfigRepository | user_config | get / set / all |
| UsageRepository | usage_records | record / summary |

小技巧：三个管理员都重复"meta 是 JSON 字符串要还原"的逻辑，抽了私有方法 `_fetch()` 共用 —— 这叫 DRY（Don't Repeat Yourself，别写重复代码）。

## 今天踩的坑：外键约束保护数据

报错 `sqlite3.IntegrityError: FOREIGN KEY constraint failed`：
- chunks 声明了 `document_id REFERENCES documents(id)`；
- 测试却直接塞 `document_id=1`，而 documents 表里没有 1 号文档；
- 数据库拒绝：**引用的对象不存在 → 不许存**。

修复 = 先建文档再建分块（真实流程本来就如此）。
教训：外键是"数据完整性保险丝"，报错不是 bug，是它在帮你 —— 遇到先想"我的数据顺序对不对"，而不是急着关掉约束。

## P0-2 收官盘点（Storage 数据层 ✅）

- 1 个数据库文件管理（Database + 7 张表 + 索引）
- 5 个 Repository：Conversation / Document / Chunk / Config / Usage
- 数据模型：MessageCreate / DocumentCreate
- 测试 **12 passed**：test_health(2) + test_database(2) + test_repositories(8)
- commits：1540e88 → ead2232 → 433e534

## 命令速记

```powershell
cd "D:\RAG个人AI助手\backend"
.\venv\Scripts\python -m pytest          # 全绿 12 passed
```
