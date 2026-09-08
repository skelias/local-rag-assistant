# 第 5 课：数据库 / SQLite / async

## 核心概念

| 词 | 一句话 |
|---|---|
| 数据库 | 装数据的"档案柜"，按表组织 |
| 表 / 行 / 列 | 一张表 = 一个种类；行 = 一条记录；列 = 一种属性 |
| 主键 PRIMARY KEY | 每行的"身份证号"，唯一 |
| 外键 REFERENCES | 指向另一张表的 id，表示关联关系（如消息→对话） |
| 索引 INDEX | 给常用查询列建"目录"，加快查找 |
| SQL | 跟数据库说话的语言（CREATE TABLE / INSERT / SELECT…） |
| SQLite | 文件型数据库：整个库 = 一个文件（data/rag.db），零配置 |
| async / await | async def = 定义"可能等待"的函数；await = 等待异步结果且不阻塞别人 |
| aiosqlite | SQLite 的异步版（本项目用它） |

## 我们建的 7 张表（数据骨架）

conversations(对话) → messages(消息, conv_id 外键) / documents(文档, 状态机) → chunks(分块, document_id 外键) / jobs(任务) / user_config(设置) / usage_records(用量)
全部带 kb_id（多知识库预留，先填 1）。

## 本次写的东西

- `backend/pytest.ini`：`asyncio_mode=auto`（async 测试免装饰器）、`testpaths=tests`
  ⚠️ 教训：ini 值后面**不能跟行尾注释**（`值  # 注释` 会被整个当成值 → pytest 报"file not found: #"），注释要单独一行
- `backend/tests/test_database.py`：两个 async 测试（建文件+建表 / 能插入能查询）
- `backend/app/models/database.py`：`SCHEMA`（建表 SQL 图纸）+ `Database` 类（init/close/conn）

## Database 类要点

- `Database(path)` → `await db.init()`（建目录→连文件→建表）→ 用 `db.conn` 执行 SQL → `await db.close()`
- `row_factory = aiosqlite.Row`：查出来的行能像字典一样 `row["列名"]` 取值
- 测试用 `tmp_path` 临时目录：每场测试独立小文件，互不污染

## 命令速记

```powershell
cd "D:\RAG个人AI助手\backend"
.\venv\Scripts\python -m pytest        # 跑全部测试（应 4 passed）
.\venv\Scripts\python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple 库名   # 国内镜像装库
```
