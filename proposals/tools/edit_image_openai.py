"""既存の画像を gpt-image-2 で編集する。

使い方: python3 proposals/tools/edit_image_openai.py 入力.png 出力.png "編集の指示"
OPENAI_API_KEY は ikedaosushi/pyconjp/.env から読む（ユーザーの指定）。
"""

import base64
import os
import sys
from pathlib import Path

import requests

ENV = Path("/Users/yutaro/ghq/ikedaosushi-github.com/ikedaosushi/pyconjp/.env")
for line in ENV.read_text().splitlines():
    if line.startswith("OPENAI_API_KEY="):
        os.environ.setdefault("OPENAI_API_KEY", line.split("=", 1)[1].strip().strip('"'))

src, dst, prompt = sys.argv[1], sys.argv[2], sys.argv[3]
with open(src, "rb") as f:
    r = requests.post(
        "https://api.openai.com/v1/images/edits",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        data={"model": "gpt-image-2", "prompt": prompt, "size": "1536x1024", "n": "1"},
        files={"image": (Path(src).name, f, "image/png")},
        timeout=600,
    )
if not r.ok:
    raise RuntimeError(f"{r.status_code}: {r.text[:500]}")
Path(dst).write_bytes(base64.b64decode(r.json()["data"][0]["b64_json"]))
print(dst)
