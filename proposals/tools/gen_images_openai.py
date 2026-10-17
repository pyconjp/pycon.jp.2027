"""タイトルの書体案を gpt-image-2 で生成する（nano banana 版と同じ指示）。

使い方: python3 proposals/tools/gen_images_openai.py [名前 ...]
OPENAI_API_KEY は ikedaosushi/pyconjp/.env から読む（ユーザーの指定）。
"""

import base64
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ENV = Path("/Users/yutaro/ghq/ikedaosushi-github.com/ikedaosushi/pyconjp/.env")
for line in ENV.read_text().splitlines():
    if line.startswith("OPENAI_API_KEY="):
        os.environ.setdefault("OPENAI_API_KEY", line.split("=", 1)[1].strip().strip('"'))

OUT = Path(__file__).resolve().parent.parent / "img" / "variants"
BASE = ("A typographic title lockup for a Python developer conference, exactly three centered lines, nothing else: "
        "line 1 (largest): \"PyCon JP 2027\"; line 2 (medium): \"2027.9.24 FRI - 26 SUN\"; "
        "line 3 (smaller, Japanese): \"静岡・沼津プラサヴェルデ\". Spell every character exactly and legibly. ")
TAIL = (" Plain pure white background, no other text, no logos, no pictures, no frame, wide composition with "
        "generous margins.")
STYLES = {
    "retro": "Style: 1960s Japanese retro travel-poster lettering, bold condensed letters with a thin inline stripe, "
             "two flat colors only: deep indigo blue and warm vermilion, slight print texture.",
    "round": "Style: chunky friendly rounded display lettering (like soft bubble letters), thick and bouncy, filled "
             "with deep ocean blue and a small white highlight on each letter, playful summer festival mood.",
    "deco": "Style: elegant Art Deco display lettering, tall high-contrast serif letters with fine hairlines and a "
            "few wave-shaped swashes, single color deep navy blue, refined and festive.",
}


def generate(key: str) -> str:
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        json={"model": "gpt-image-2", "prompt": BASE + STYLES[key] + TAIL, "size": "1536x1024", "n": 1},
        timeout=600,
    )
    if not r.ok:
        raise RuntimeError(f"{key}: {r.status_code}: {r.text[:500]}")
    raw = base64.b64decode(r.json()["data"][0]["b64_json"])
    path = OUT / f"type-gpt-{key}.png"
    path.write_bytes(raw)
    return f"{path.name} {len(raw) // 1024}KB"


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=3) as ex:
        for msg in ex.map(generate, sys.argv[1:] or list(STYLES)):
            print(msg, flush=True)
