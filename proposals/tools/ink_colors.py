"""筆文字の透過PNG（タイトル・日付・会場）を、墨の色だけ替えた色違いで書き出す。

使い方: python3 proposals/tools/ink_colors.py
入力: img/logo/brush.png（墨＋朱の落款）、img/logo/date-blue.png、img/logo/venue-blue.png
出力: img/logo/{title,date,venue}-{ai,white,sumi}.png
落款（赤みの強い画素）は色を替えない。
"""

from pathlib import Path

import numpy as np
from PIL import Image

LOGO = Path(__file__).resolve().parent.parent / "img" / "logo"
INKS = {
    "ai": (16, 46, 120),      # 藍
    "white": (255, 255, 255),
    "sumi": (24, 24, 28),     # 墨
}
SOURCES = {"title": "brush.png", "date": "date-blue.png", "venue": "venue-blue.png"}


def recolor(src: Image.Image, ink) -> Image.Image:
    im = np.asarray(src.convert("RGBA")).astype(np.float32)
    r, g, b, a = im[..., 0], im[..., 1], im[..., 2], im[..., 3]
    seal = (r - np.maximum(g, b)) > 60
    lum = (r * 0.3 + g * 0.59 + b * 0.11) / 255
    col = np.array(ink, np.float32)
    if ink == INKS["white"]:
        # 白はかすれ（明るい部分）を少し透かして筆の濃淡を残す
        rgb = np.broadcast_to(col, im[..., :3].shape)
        a = np.where(seal, a, a * np.clip(1.15 - lum * 0.6, 0.55, 1))
    else:
        rgb = np.clip(col * np.clip(0.7 + lum[..., None] * 1.1, 0.7, 1.6), 0, 255)
    out = im.copy()
    out[..., :3] = np.where(seal[..., None], im[..., :3], rgb)
    out[..., 3] = a
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def main():
    for name, file in SOURCES.items():
        src = Image.open(LOGO / file)
        for ink_name, ink in INKS.items():
            dst = LOGO / f"{name}-{ink_name}.png"
            recolor(src, ink).save(dst, optimize=True)
            print(dst.name)


if __name__ == "__main__":
    main()
