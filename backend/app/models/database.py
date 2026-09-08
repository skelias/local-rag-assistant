"""数据库模块：负责打开/初始化 SQLite 文件，并一次性建好所有表。

- Database 类 = 数据库的连接管理器（打开 / 建表 / 关闭）
- SCHEMA 变量 = 一长串 SQL 建表语句（"档案柜的图纸"）
- aiosqlite = SQLite 的异步版（配合 async/await 使用）
"""
import aiosqlite
from pathlib import Path

# ---------------- "档案柜图纸"：所有表 ---------------- #
SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- 对话表：一场场对话
CREATE TABLE IF NOT EXISTS conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,          -- 主键，自动编号
  kb_id INTEGER NOT NULL DEFAULT 1,              -- 属于哪个知识库（多库预留）
  title TEXT NOT NULL DEFAULT '新对话',
  model TEXT,                                    -- 这场对话用的模型
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 消息表：对话里的每条消息
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conv_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,  -- 外键→对话
  role TEXT NOT NULL CHECK (role IN ('user','assistant','system')),         -- 谁说的
  content TEXT NOT NULL,                                                    -- 说了什么
  sources TEXT,          -- AI 回答的来源引用，存 JSON 字符串
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 文档表：用户上传的文档（含状态机：uploading→parsed→ready/failed）
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kb_id INTEGER NOT NULL DEFAULT 1,
  filename TEXT NOT NULL,
  file_type TEXT NOT NULL,
  file_path TEXT NOT NULL,
  size INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'uploading',
  error TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 分块表：文档被切成的碎块（正文检索的最小单位）
CREATE TABLE IF NOT EXISTS chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kb_id INTEGER NOT NULL DEFAULT 1,
  document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,  -- 外键→文档
  seq INTEGER NOT NULL,                                                     -- 第几块
  text TEXT NOT NULL,                                                       -- 块的内容
  meta TEXT NOT NULL DEFAULT '{}',                                          -- JSON：页码/语言等
  status TEXT NOT NULL DEFAULT 'pending',      -- pending 待索引 / indexed 已入向量库
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 任务表：后台任务（解析/索引等）记录
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kb_id INTEGER NOT NULL DEFAULT 1,
  document_id INTEGER NOT NULL,
  kind TEXT NOT NULL,                          -- parse | index
  status TEXT NOT NULL DEFAULT 'queued',       -- queued|running|done|failed
  progress INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 设置表：键值对（模型选择、检索参数等，运行时可改）
CREATE TABLE IF NOT EXISTS user_config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL                            -- JSON 编码的值
);

-- 用量表：每次 AI 调用消耗多少 token + 缓存命中情况（不计费，只统计）
-- 输入 token = cache_hit_tokens + cache_miss_tokens；命中率 = 命中 / 输入
CREATE TABLE IF NOT EXISTS usage_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  model TEXT NOT NULL,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  cache_hit_tokens INTEGER NOT NULL DEFAULT 0,
  cache_miss_tokens INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 索引：给常用的"按什么查"建目录，查询更快
CREATE INDEX IF NOT EXISTS idx_docs_kb ON documents(kb_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_kb ON chunks(kb_id);
CREATE INDEX IF NOT EXISTS idx_msgs_conv ON messages(conv_id);
"""


class Database:
    """SQLite 连接管理器：init() 建文件+建表，close() 关闭。"""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self._conn: aiosqlite.Connection | None = None

    async def init(self) -> None:
        # 确保 data/ 这类父目录存在（不存在会报错）
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # aiosqlite.connect() = 打开（不存在则创建）数据库文件
        self._conn = await aiosqlite.connect(self.db_path)
        # row_factory=Row：查出来的每一行可以像字典一样 row["列名"] 取值
        self._conn.row_factory = aiosqlite.Row
        # executescript 一次执行整段 SCHEMA（建表语句，IF NOT EXISTS=已存在则跳过）
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    @property
    def conn(self) -> aiosqlite.Connection:
        """拿到底层连接，供 Repository 层使用。"""
        if self._conn is None:
            raise RuntimeError("Database not initialized — 先 await db.init()")
        return self._conn

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
