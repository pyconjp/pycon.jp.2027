#!/usr/bin/env python3
"""Pixelate the participants' names in the 2026-10-26 huddle recording.

Run with:
  python3 proposals/tools/mosaic_huddle.py "/Users/yutaro/Screenshots/CleanShot 2026-10-26 at 21.03.34.gif"

The original recording stays outside the repository. This writes the
mosaicked copy to proposals/img/blog/2026-10-venue-visit/huddle.gif, which
optimize_images.py then turns into huddle.webp and huddle-still.webp.
Each rectangle is pixelated only in the frames where its label is on screen:
after the labels disappear (frame 60), Shogo Yasuda's face moves into the
top-row label band, so pixelating there would cover a face.
The rectangles cover the labels only, not faces.
"""

import sys
from pathlib import Path

from PIL import Image


OUTPUT = Path(__file__).resolve().parents[1] / "img/blog/2026-10-venue-visit/huddle.gif"
# The rectangles below are measured on this exact recording.
EXPECTED_SIZE = (800, 453)
EXPECTED_FRAMES = 75
BLOCK = 8
# Frames 0-59 show every tile's name label (the pointer is over the grid);
# frames 60-74 show only the mute icons. Frames 0-58 also show the
# "Koya Nakamura / View profile" tooltip over the top row.
LABEL_FRAMES = range(0, 60)
TOOLTIP_FRAMES = range(0, 59)
# (frames, (left, top, right, bottom)) in pixels. Each tile's name label sits
# at its bottom-left; the widths include the speaker icon or "..." shown
# before a name in some frames.
NAME_RECTANGLES = (
    # Top row (labels at y 140-154)
    (LABEL_FRAMES, (54, 138, 122, 156)),   # Yutaro Ikeda
    (LABEL_FRAMES, (197, 138, 254, 156)),  # 槇野未来
    (LABEL_FRAMES, (342, 139, 396, 156)),  # Shogo Yasuda ("Shogo Ya" beside the tooltip)
    (LABEL_FRAMES, (485, 138, 540, 156)),  # Hiroshi Sano
    (LABEL_FRAMES, (629, 138, 737, 156)),  # Nyoho (KITADAI, Yukinori)
    (TOOLTIP_FRAMES, (373, 142, 442, 174)),  # Koya Nakamura / View profile
    # Middle row (labels at y 284-297)
    (LABEL_FRAMES, (55, 282, 124, 299)),   # Yoshiharu Tanabe
    (LABEL_FRAMES, (198, 282, 280, 299)),  # Takeshi Sugiyama
    (LABEL_FRAMES, (342, 282, 416, 299)),  # Koya Nakamura
    (LABEL_FRAMES, (485, 282, 559, 299)),  # Hikaru Yamada
    (LABEL_FRAMES, (629, 282, 684, 299)),  # 鈴木まー
    # Bottom row (labels at y 427-441)
    (LABEL_FRAMES, (127, 425, 188, 443)),  # okaits7534
    (LABEL_FRAMES, (269, 425, 338, 443)),  # Haruki Inoue
    (LABEL_FRAMES, (410, 425, 495, 443)),  # Peacock (Yoichi Takai)
    (LABEL_FRAMES, (557, 425, 608, 443)),  # akiko_m
)


def pixelate(frame: Image.Image, box: tuple[int, int, int, int]) -> None:
    region = frame.crop(box)
    small = region.resize(
        (max(1, region.width // BLOCK), max(1, region.height // BLOCK)), Image.Resampling.BOX
    )
    frame.paste(small.resize(region.size, Image.Resampling.NEAREST), box)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: mosaic_huddle.py <original huddle gif>")
    source = Path(sys.argv[1])
    frames, durations = [], []
    with Image.open(source) as recording:
        if recording.size != EXPECTED_SIZE or recording.n_frames != EXPECTED_FRAMES:
            raise ValueError(
                f"Expected a {EXPECTED_SIZE} GIF with {EXPECTED_FRAMES} frames, got "
                f"{recording.size} with {recording.n_frames}: the rectangles would not match"
            )
        for index in range(recording.n_frames):
            recording.seek(index)
            frame = recording.convert("RGB")
            for frames_with_name, box in NAME_RECTANGLES:
                if index in frames_with_name:
                    pixelate(frame, box)
            frames.append(frame)
            durations.append(recording.info["duration"])
    frames[0].save(
        OUTPUT, "GIF", save_all=True, append_images=frames[1:], duration=durations, loop=0,
    )
    print(f"{OUTPUT} ({OUTPUT.stat().st_size:,} bytes; {len(frames)} frames)")


if __name__ == "__main__":
    main()
