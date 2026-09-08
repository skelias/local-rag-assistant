"""冒烟测试：确认项目基础能跑起来。

测试文件的规则：
- 文件名以 test_ 开头（pytest 才会找到它）
- 函数名以 test_ 开头
- 里面写 assert 断言：条件为真 → 通过(绿)；为假 → 失败(红)
"""


def test_settings_module_importable():
    """能导入 app.core.config 里的 Settings 类（现在 config.py 还不存在，应该红）。"""
    from app.core.config import Settings  # noqa: F401

    assert Settings is not None


def test_settings_data_dir_points_to_data():
    """配置对象默认的 DATA_DIR 名字应为 data（数据目录约定）。"""
    from app.core.config import Settings

    s = Settings()
    assert s.DATA_DIR.name == "data"
