"""冒烟：profile 上传 + 媒体访问（httpx 同步版，供命令行快速自检）。"""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = "http://127.0.0.1:8000"


def main() -> None:
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
        "1f15c4890000000a49444154789c636000000200010005fe02fe000000"
        "0049454e44ae426082"
    )
    with httpx.Client(timeout=15) as c:
        print("health:", c.get(f"{BASE}/api/health").json())
        print("profile-before:", c.get(f"{BASE}/api/profile").json())
        r = c.post(f"{BASE}/api/profile/upload", params={"kind": "background"},
                   files={"file": ("bg.png", png, "image/png")})
        print("upload:", r.status_code, r.json())
        url = r.json()["url"]
        img = c.get(f"{BASE}{url}")
        print("media:", img.status_code, img.headers.get("content-type"))
        print("profile-after:", c.get(f"{BASE}/api/profile").json())


if __name__ == "__main__":
    main()
