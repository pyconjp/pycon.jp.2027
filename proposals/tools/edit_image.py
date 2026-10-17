"""既存の画像を nano banana (gemini-3.1-flash-image) で編集する。

使い方: python3 proposals/tools/edit_image.py 入力.jpg 出力.jpg "編集の指示"
"""

import base64
import json
import os
import sys
from pathlib import Path

import requests

ENV = Path("/Users/yutaro/ghq/github.com/ramencloud/ddi-client/.env")
for line in ENV.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent"
src, dst, prompt = sys.argv[1], sys.argv[2], sys.argv[3]
body = {"contents": [{"parts": [
            {"inlineData": {"mimeType": "image/jpeg", "data": base64.b64encode(Path(src).read_bytes()).decode()}},
            {"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]}}
r = requests.post(URL, headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"},
                  json=body, timeout=300)
if not r.ok:
    raise RuntimeError(f"{r.status_code}: {r.text[:500]}")
parts = r.json()["candidates"][0]["content"]["parts"]
imgs = [p for p in parts if "inlineData" in p]
if not imgs:
    raise RuntimeError(f"no image in response: {json.dumps(parts)[:500]}")
Path(dst).write_bytes(base64.b64decode(imgs[0]["inlineData"]["data"]))
print(dst)
