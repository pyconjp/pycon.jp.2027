"""2026年の写真を引きで切り出し、フェルトの当て布で囲んだ透過 webp を作る。

使い方: python3 proposals/tools/felt_frames.py
出力: proposals/img/felt/felt-1.webp 〜 felt-6.webp
"""

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent / "img"
OUT = ROOT / "felt"
OUT.mkdir(parents=True, exist_ok=True)

S = 2                      # 2倍で描いて縮小し、輪郭をなめらかにする
W, H = 560 * S, 440 * S    # 当て布の画像の大きさ
BORDER = 30 * S            # 布の縁の幅（写真の外側）
STITCH = 13 * S            # 布の外周から縫い目までの距離

# (写真, 切り出し範囲 x0, y0, x1, y1, 布の色)  座標は img/2026 の 1400px 版
FRAMES = [
    ("reception", 40, 140, 1000, 860, (243, 233, 210)),   # 生成り
    ("prep", 150, 0, 1250, 825, (238, 138, 44)),          # みかん
    ("staff", 150, 100, 1250, 925, (91, 175, 106)),       # 茶葉
    ("setup", 0, 0, 1400, 1050, (242, 194, 48)),          # 黄
    ("crowd", 300, 150, 1300, 900, (233, 101, 90)),       # 朱
    ("group", 78, 0, 1323, 934, (251, 250, 246)),         # 白
]


def blob(w, h, inset, seed, wobble):
    """角の丸い四角を少しゆがませた閉曲線の点列"""
    rnd = random.Random(seed)
    phases = [rnd.uniform(0, 6.28) for _ in range(3)]
    cx, cy = w / 2, h / 2
    a, b = w / 2 - inset, h / 2 - inset
    pts = []
    for i in range(360):
        t = math.radians(i)
        c, s = math.cos(t), math.sin(t)
        # 超楕円（n=4）で角丸四角に近い形を作る
        r = (abs(c) ** 4 / a ** 4 + abs(s) ** 4 / b ** 4) ** (-1 / 4)
        r += wobble * (math.sin(2 * t + phases[0]) + 0.6 * math.sin(3 * t + phases[1]) + 0.3 * math.sin(5 * t + phases[2]))
        pts.append((cx + r * c, cy + r * s))
    return pts


def felt_texture(size, color, seed):
    """フェルトの毛羽: 色の細かなむらと、短い繊維の線"""
    rng = np.random.default_rng(seed)
    w, h = size
    noise = rng.normal(0, 1, (h // 3, w // 3)).astype(np.float32)
    noise = np.asarray(Image.fromarray(noise).resize((w, h), Image.BICUBIC))
    base = np.array(color, np.float32)[None, None, :] * (1 + 0.05 * noise[..., None])
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    fibers = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(fibers)
    rnd = random.Random(seed)
    for _ in range(w * h // 900):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        ang, ln = rnd.uniform(0, 6.28), rnd.uniform(4, 12) * S / 2
        light = rnd.random() < 0.5
        col = (255, 255, 255, 46) if light else (0, 0, 0, 30)
        d.line([(x, y), (x + ln * math.cos(ang), y + ln * math.sin(ang))], fill=col, width=1)
    img = img.convert("RGBA")
    img.alpha_composite(fibers)
    return img


def dashed(draw, pts, dash, gap, fill, width):
    """閉曲線に沿って破線（縫い目）を描く"""
    seg, on, acc = [], True, 0.0
    loop = pts + [pts[0]]
    for (x0, y0), (x1, y1) in zip(loop, loop[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        pos = 0.0
        while pos < L:
            step = min((dash if on else gap) - acc, L - pos)
            nx, ny = x0 + (x1 - x0) * (pos + step) / L, y0 + (y1 - y0) * (pos + step) / L
            if on:
                if not seg:
                    seg.append((x0 + (x1 - x0) * pos / L, y0 + (y1 - y0) * pos / L))
                seg.append((nx, ny))
            pos += step
            acc += step
            if acc >= (dash if on else gap) - 1e-6:
                if on and len(seg) > 1:
                    draw.line(seg, fill=fill, width=width, joint="curve")
                seg, on, acc = [], not on, 0.0
    if on and len(seg) > 1:
        draw.line(seg, fill=fill, width=width, joint="curve")


def main():
    for i, (name, x0, y0, x1, y1, color) in enumerate(FRAMES, 1):
        outer = blob(W, H, 2 * S, seed=i, wobble=6 * S)
        inner = blob(W, H, BORDER, seed=i + 50, wobble=4 * S)
        stitch = blob(W, H, STITCH, seed=i, wobble=5 * S)

        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).polygon(outer, fill=255)
        felt = felt_texture((W, H), color, seed=i)

        photo = Image.open(ROOT / "2026" / f"{name}.jpg").convert("RGB").crop((x0, y0, x1, y1))
        photo = photo.resize((W, H), Image.LANCZOS).convert("RGBA")
        pmask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(pmask).polygon(inner, fill=255)
        # 写真の縁に布の影を落とし、当て布に縫い付けたように見せる
        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shade.putalpha(ImageChops.subtract(pmask, pmask.filter(ImageFilter.GaussianBlur(6 * S)).point(lambda v: v)).point(lambda v: min(255, v * 2)))
        felt.paste(photo, (0, 0), pmask)
        felt.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 0)))
        edge = Image.new("RGBA", (W, H), (20, 20, 20, 0))
        edge.putalpha(ImageChops.subtract(pmask, pmask.filter(ImageFilter.MinFilter(5 * S + 1))).point(lambda v: v // 3))
        felt.alpha_composite(edge)

        d = ImageDraw.Draw(felt)
        light = sum(color) > 600
        dashed(d, stitch, dash=11 * S, gap=8 * S, fill=(120, 110, 95, 230) if light else (255, 255, 255, 235), width=3 * S)

        felt.putalpha(ImageChops.multiply(felt.getchannel("A"), mask))
        felt = felt.resize((W // S, H // S), Image.LANCZOS)
        felt.save(OUT / f"felt-{i}.webp", quality=86)
        print(f"felt-{i}.webp", name, felt.size)


if __name__ == "__main__":
    main()
