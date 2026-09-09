"""从 ModelScope（国内 CDN）下载 BGE-M3 到 data/models/bge-m3，避免慢速/不可达的 HuggingFace。

用法：venv/Scripts/python scripts/download_bge_m3.py
（真实端到端 real_e2e.py 检测到本地目录存在后会自动用本地模型。）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import Settings                              # noqa: E402

if __name__ == "__main__":
    target = Settings().DATA_DIR / "models" / "bge-m3"
    print("下载目标：", target)
    from modelscope import snapshot_download
    p = snapshot_download("BAAI/bge-m3", local_dir=str(target))
    print("完成：", p)
