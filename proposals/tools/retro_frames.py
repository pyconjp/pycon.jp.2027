"""2026年の写真を、レトロな書体に合わせた枠（切手風・エアメール風）で囲んだ透過 webp を作る。

使い方: python3 proposals/tools/retro_frames.py
出力: proposals/img/retro/stamp-1.webp 〜 stamp-6.webp, airmail-1.webp 〜 airmail-6.webp
写真は少し色あせた印刷風（彩度を落とし、生成り寄りにする）にする。
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent / "img"
OUT = ROOT / "retro"
OUT.mkdir(parents=True, exist_ok=True)

S = 2
W, H = 560 * S, 440 * S
AI = (24, 72, 150)        # 藍（書体の青に合わせる）
SHU = (226, 78, 50)       # 朱
KINARI = (247, 241, 226)  # 生成り

# 写真と切り出し範囲（img/2026 の 1400px 版の座標）。felt_frames.py と同じ構図
FRAMES = [
    ("reception", 40, 140, 1000, 860),
    ("prep", 150, 0, 1250, 825),
    ("staff", 150, 100, 1250, 925),
    ("setup", 0, 0, 1400, 1050),
    ("crowd", 300, 150, 1300, 900),
    ("group", 78, 0, 1323, 934),
]


def faded(name, box, size):
    """色あせた印刷風: 彩度とコントラストを落とし、生成りを薄く重ねる"""
    im = Image.open(ROOT / "2026" / f"{name}.jpg").convert("RGB").crop(box).resize(size, Image.LANCZOS)
    im = ImageEnhance.Color(im).enhance(0.72)
    im = ImageEnhance.Contrast(im).enhance(0.92)
    tint = Image.new("RGB", size, KINARI)
    return Image.blend(im, tint, 0.12)


def stamp(i, name, box):
    """切手風: 生成りの台紙、縁はミシン目（半円の切り欠き）、内側に藍の細い罫"""
    m = 26 * S                       # 台紙の幅
    r = 7 * S                        # ミシン目の半径
    step = 22 * S
    img = Image.new("RGBA", (W, H), KINARI + (255,))
    mask = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(mask)
    for x in range(step // 2, W, step):
        d.ellipse((x - r, -r, x + r, r), fill=0)
        d.ellipse((x - r, H - r, x + r, H + r), fill=0)
    for y in range(step // 2, H, step):
        d.ellipse((-r, y - r, r, y + r), fill=0)
        d.ellipse((W - r, y - r, W + r, y + r), fill=0)
    img.paste(faded(name, box, (W - 2 * m, H - 2 * m)), (m, m))
    dd = ImageDraw.Draw(img)
    dd.rectangle((m - 6 * S, m - 6 * S, W - m + 6 * S, H - m + 6 * S), outline=AI + (255,), width=2 * S)
    img.putalpha(mask)
    return img


def airmail(i, name, box):
    """エアメール風: 縁に藍と朱の斜めストライプ、内側に白の余白"""
    b = 20 * S                       # ストライプの幅
    pad = 8 * S                      # 写真まわりの白
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    stripe = Image.new("RGB", (W + H, H), (255, 255, 255))
    ds = ImageDraw.Draw(stripe)
    period = 36 * S
    for k, x in enumerate(range(-H, W + H, period // 3)):
        col = (AI, (255, 255, 255), SHU)[k % 3]
        ds.polygon([(x, H), (x + period // 3, H), (x + period // 3 + H, 0), (x + H, 0)], fill=col)
    stripe = stripe.crop((0, 0, W, H))
    img.paste(stripe, (0, 0))
    ImageDraw.Draw(img).rectangle((b, b, W - b, H - b), fill=(255, 255, 255, 255))
    img.paste(faded(name, box, (W - 2 * (b + pad), H - 2 * (b + pad))), (b + pad, b + pad))
    corner = Image.new("L", (W, H), 0)
    ImageDraw.Draw(corner).rounded_rectangle((0, 0, W - 1, H - 1), radius=6 * S, fill=255)
    img.putalpha(corner)
    return img


def main():
    for i, (name, *box) in enumerate(FRAMES, 1):
        for kind, fn in (("stamp", stamp), ("airmail", airmail)):
            im = fn(i, name, tuple(box)).resize((W // S, H // S), Image.LANCZOS)
            im.save(OUT / f"{kind}-{i}.webp", quality=86)
    print("ok", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
