"""数据库层测试：Database 类能把 SQLite 文件建出来，并建好所有表。

测试用 tmp_path（pytest 提供的临时目录）—— 每场测试用独立小文件，互不污染。
async 测试函数：pytest.ini 里开了 asyncio_mode=auto，直接 async def 即可。
"""


async def test_init_creates_db_file_and_all_tables(tmp_path):
    from app.models.database import Database

    db = Database(tmp_path / "t.db")
    await db.init()

    # 1) 数据库文件真的生成了
    assert (tmp_path / "t.db").exists()

    # 2) 该有的表都建出来了（查 SQLite 自己的"表目录" sqlite_master）
    cur = await db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    rows = await cur.fetchall()
    names = {r["name"] for r in rows}

    expect = {"conversations", "messages", "documents", "chunks",
              "jobs", "user_config", "usage_records"}
    missing = expect - names
    assert not missing, f"缺少表: {missing}"

    await db.close()


async def test_database_can_insert_and_query(tmp_path):
    from app.models.database import Database

    db = Database(tmp_path / "t2.db")
    await db.init()

    # 往 conversations 表插一行，再查回来 —— 证明"能写能读"
    cur = await db.conn.execute(
        "INSERT INTO conversations(kb_id, title, model) VALUES(?,?,?)",
        (1, "第一场对话", "claude-sonnet-4-5"),
    )
    await db.conn.commit()

    cur = await db.conn.execute("SELECT title, model FROM conversations")
    row = await cur.fetchone()
    assert row["title"] == "第一场对话"
    assert row["model"] == "claude-sonnet-4-5"

    await db.close()
