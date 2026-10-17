"""案Aの画像素材を nano banana (gemini-3.1-flash-image) で生成する。

使い方: python3 proposals/tools/gen_images.py [名前 ...]   （省略時は全部）
GEMINI_API_KEY は ddi-client の .env から読む（ユーザーの許可済み）。
"""

import base64
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ENV = Path("/Users/yutaro/ghq/github.com/ramencloud/ddi-client/.env")
for line in ENV.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-3.1-flash-image"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
OUT = Path(__file__).resolve().parent.parent / "img" / "variants"
OUT.mkdir(parents=True, exist_ok=True)

NO_TEXT = " Absolutely no text, no letters, no numbers, no signature, no seal, no logos, no watermark."
IMAGES = {
    "sora-sea": ("Bright summer photograph, slightly faded film look: view across Suruga Bay from the Numazu coast in "
                 "Shizuoka. Clear deep blue sky with NO clouds at all (only a soft pale haze near the horizon). The horizon "
                 "line sits at about 58 percent of the image height. Mount Fuji with a little snow stands centered on the "
                 "horizon, not too large. The lower 40 percent is the open sea: deep blue water with gentle waves and "
                 "sparkling sunlight reflections, a few tiny distant fishing boats, and only a very thin strip of sand "
                 "beach with small surf at the very bottom edge. No people." + NO_TEXT, "16:9"),
    "cloud-a": ("Several big fluffy white summer cumulus clouds, bright white tops and soft light-gray shading, spread "
                "horizontally across the frame with gaps between them, isolated on a perfectly solid pure black "
                "background, photographic, soft edges." + NO_TEXT, "21:9"),
    "cloud-b": ("A few small and medium wispy white summer clouds, thin and soft, scattered horizontally with large gaps, "
                "isolated on a perfectly solid pure black background, photographic, soft edges." + NO_TEXT, "21:9"),
    "cloud-py": ("One single fluffy white summer cumulus cloud whose overall silhouette clearly resembles the Python "
                 "programming language logo: two interlocking rounded snake-like shapes, one at the upper left facing "
                 "right and one at the lower right facing left, overlapping in the middle, each with one small round "
                 "hole like an eye. It must still look like a real soft photographic cloud with bright white tops and "
                 "light-gray shading, not a flat icon. Centered, generous margin, on a perfectly solid pure black "
                 "background." + NO_TEXT, "1:1"),
    "cloud-frame": ("A fluffy white summer cumulus cloud formed into a round wreath frame: soft puffy cloud lumps all around "
                    "a clean empty circular hole in the exact center (the hole is about 55 percent of the image width and "
                    "is pure black), thicker and puffier at the bottom and sides, photographic soft cloud with bright "
                    "white tops and light-gray shading, everything else perfectly solid pure black background." + NO_TEXT, "1:1"),
    **{f"type-nb-{k}": (
        "A typographic title lockup for a Python developer conference, exactly three centered lines, nothing else: "
        "line 1 (largest): \"PyCon JP 2027\"; line 2 (medium): \"2027.9.24 FRI - 26 SUN\"; "
        "line 3 (smaller, Japanese): \"静岡・沼津プラサヴェルデ\". Spell every character exactly and legibly. "
        + style + " Plain pure white background, no other text, no logos, no pictures, no frame, wide composition "
        "with generous margins.", "16:9") for k, style in {
        "retro": "Style: 1960s Japanese retro travel-poster lettering, bold condensed letters with a thin inline stripe, "
                 "two flat colors only: deep indigo blue and warm vermilion, slight print texture.",
        "round": "Style: chunky friendly rounded display lettering (like soft bubble letters), thick and bouncy, filled "
                 "with deep ocean blue and a small white highlight on each letter, playful summer festival mood.",
        "deco": "Style: elegant Art Deco display lettering, tall high-contrast serif letters with fine hairlines and a "
                "few wave-shaped swashes, single color deep navy blue, refined and festive.",
    }.items()},
    **{f"bg-{k}": (
        "Bright summer photograph with a slightly faded film look, Numazu, Shizuoka, Japan. " + scene + " The sky is a "
        "clean, clear deep blue summer sky with NO clouds at all (only a soft pale haze near the horizon) and occupies the "
        "top 70 percent of the frame, calm enough to place a large title on it. The horizon and landscape sit in the "
        "bottom 30 percent. No people." + NO_TEXT, "4:3") for k, scene in {
        "senbon-wide": "A wide view of the long curving Senbonmatsubara pine beach, the open blue Suruga Bay on the "
                       "right, and a large snow-capped Mount Fuji rising over the bay in the distance.",
        "port": "Numazu fishing port with a few colorful fishing boats moored at the quay and the tall water-gate "
                "tower by the harbor, Mount Fuji visible far behind.",
        "osezaki": "The rocky Osezaki cape of western Izu with a small pine grove at its tip, clear turquoise sea, and "
                   "Mount Fuji seen across the bay.",
        "fuji": "A majestic, very large snow-capped Mount Fuji rising across Suruga Bay, seen from the Numazu coast, "
                "its slopes spanning nearly the full width of the frame and its summit reaching the middle of the image, "
                "clear blue sea and a thin strip of pine-lined sand beach in the foreground.",
        "dusk": "Golden-hour view across Suruga Bay from the Numazu beach, warm peach and gold light on the sea, Mount "
                "Fuji in soft violet silhouette; the sky fades from deep blue at the top to warm gold at the horizon.",
    }.items()},
    **{f"team-{k}": (
        "Black and white hand-drawn character illustration in a bold, friendly editorial style: confident brush-pen "
        "outlines with varying thick-to-thin line weight, large areas of SOLID BLACK fill for hair and trousers, white "
        "shirts, small round heads with calm closed-eye smiles and tiny noses, slightly elongated playful proportions, "
        "a few scattered small black dots and short motion marks around the figures for liveliness, no gray shading, "
        "no gradients, no color, pure black on a pure white background, generous margin, centered. Scene: " + scene
        + NO_TEXT, "1:1") for k, scene in {
        "program": "a person standing at a small podium giving a talk, with a big speech bubble and a slide screen behind.",
        "venue": "a person carrying a stack of chairs and another arranging a banner stand and tables in a hall.",
        "attendee": "a smiling person at a reception desk handing a name badge and a lanyard to a visitor.",
        "sponsor": "two people shaking hands in front of a small sponsor booth with a tablecloth.",
        "pr": "a person holding a megaphone with small hearts and a phone with social media bubbles floating around.",
        "dev": "a person typing on a laptop with code brackets and a small snake curled on the desk.",
        "design": "a person with a pencil and a palette drawing a poster on an easel.",
        "local": "two people chatting in front of a small shop with Mount Fuji in the background and a tea cup.",
        "step-form": "a person sitting cross-legged happily filling in a big clipboard form with a pen, a check mark "
                     "floating nearby.",
        "step-slack": "a person holding a smartphone, with a big chat bubble containing a waving hand and a small "
                      "confetti burst popping out of the phone (being invited to a team chat).",
        "step-onboarding": "three people sitting around a small round table, one pointing at a simple map or diagram "
                           "on a sheet of paper while the others listen and smile (a welcome meeting).",
    }.items()},
    "mikan-illust": ("Flat vector-style illustration of a single Japanese mikan mandarin orange with one green leaf on a "
                     "short stem, simple clean shapes, soft flat color with one subtle highlight and a few dots for peel "
                     "texture, slightly hand-drawn friendly look, limited palette (warm orange, leaf green, a touch of "
                     "cream), no gradients, no 3D render, no gloss, no shadow on the ground, centered with generous "
                     "margin on a pure flat white background." + NO_TEXT, "1:1"),
    "tealeaf-illust": ("Flat vector-style illustration of two fresh green tea leaves joined at a short stem (Shizuoka "
                       "green tea), simple clean shapes, soft flat color with a light center vein line, slightly "
                       "hand-drawn friendly look, limited palette (two greens, a touch of cream), no gradients, no 3D "
                       "render, no gloss, no shadow on the ground, centered with generous margin on a pure flat white "
                       "background." + NO_TEXT, "1:1"),
}


def generate(name: str) -> str:
    prompt, aspect = IMAGES[name]
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect}}}
    r = requests.post(URL, headers={"x-goog-api-key": API_KEY, "Content-Type": "application/json"}, json=body, timeout=300)
    if not r.ok:
        raise RuntimeError(f"{name}: {r.status_code}: {r.text[:500]}")
    parts = r.json()["candidates"][0]["content"]["parts"]
    imgs = [p for p in parts if "inlineData" in p]
    if not imgs:
        raise RuntimeError(f"{name}: no image in response: {json.dumps(parts)[:500]}")
    raw = base64.b64decode(imgs[0]["inlineData"]["data"])
    path = OUT / f"{name}.jpg"
    path.write_bytes(raw)
    return f"{name}: {path.name} {len(raw) // 1024}KB"


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=8) as ex:
        for msg in ex.map(generate, sys.argv[1:] or list(IMAGES)):
            print(msg, flush=True)
