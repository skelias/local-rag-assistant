"""应用配置：集中管理"会变的量"（路径、密钥、默认值）。

原理：
- 继承 pydantic-settings 的 BaseSettings —— 每个类属性就是一个"配置项"；
- 启动时会自动去读仓库根目录的 .env 文件（env_file 指定）与环境变量，
  没填就用我们写在等号后面的默认值；
- 以后要加配置项：在下面加一行属性即可。
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 这个文件在 backend/app/core/config.py，往上数 4 层 = 仓库根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),   # 读仓库根的 .env（密钥放那里，不进 git）
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- 路径：本地数据都收进 data/ 一个目录（备份=拷贝它） ----
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = DATA_DIR / "uploads"     # 用户上传的原始文档
    DB_PATH: Path = DATA_DIR / "rag.db"         # SQLite 数据库文件
    QDRANT_PATH: Path = DATA_DIR / "qdrant"     # 向量库数据

    # ---- API 密钥（从 .env 读；代码里不写死） ----
    claude_api_key: str = ""
    deepseek_api_key: str = ""
    openai_api_key: str = ""
    glm_api_key: str = ""
    kimi_api_key: str = ""

    # ---- OpenAI 兼容端点的 base_url（各自默认；自建网关/代理时可覆盖） ----
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    openai_base_url: str = "https://api.openai.com/v1"
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    kimi_base_url: str = "https://api.moonshot.cn/v1"

    # ---- 模型默认值（仅兜底；真正生效值以后由数据库 user_config 提供） ----
    default_chat_provider: str = "anthropic"  # anthropic | deepseek | glm | kimi | openai
    default_chat_model: str = "claude-sonnet-4-5"
    fallback_chat_provider: str = "deepseek"
    fallback_chat_model: str = "deepseek-v4-flash"   # 官方名（deepseek-chat 已于 2026-07 停用）
    default_embedding_model: str = "bge-m3"

    # ---- Qdrant 向量库 ----
    qdrant_collection: str = "rag_documents"
    qdrant_vector_size: int = 1024              # BGE-M3 稠密向量维度

    # ---- 服务器 ----
    host: str = "127.0.0.1"
    port: int = 8000

    # ---- 上传规则 ----
    max_upload_mb: int = 100
    allowed_exts: tuple = (
        ".md", ".txt", ".markdown",
        ".py", ".js", ".ts", ".tsx", ".jsx",
        ".json", ".yaml", ".yml", ".toml", ".csv", ".html", ".css",
    )


settings = Settings()
