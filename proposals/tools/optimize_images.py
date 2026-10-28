#!/usr/bin/env python3
"""Generate WebP and AVIF assets without changing originals.

Run with: python3 proposals/tools/optimize_images.py
Requires Pillow with WebP and AVIF support. Every run starts from the original images.
"""

from pathlib import Path

from PIL import Image


IMAGES = Path(__file__).resolve().parents[1] / "img"
OUTPUT = IMAGES / "web"
# Destinations made from one frame of an animated source.
STILL_FRAMES = {
    # Frames 0-58 show a "View profile" tooltip. Frame 65 has no tooltip or
    # name labels, and its mouse cursor is not over anyone's face.
    "blog/2026-10-venue-visit/huddle-still.webp": 65,
}
MAX_ANIMATED_BYTES = 2_000_000


def image_jobs():
    """Yield (source relative to IMAGES, destination, resize axis, size, quality)."""
    for width in (1401, 800):
        yield "logo/lockup-snake-1.png", f"logo/lockup-snake-1-{width}.webp", "width", width, 88
        yield "logo/lockup-snake-1.png", f"logo/lockup-snake-1-{width}.avif", "width", width, 60
    yield "logo/header-title.png", "logo/header-title.webp", "height", 102, 90
    yield "variants/sora-clear.jpg", "variants/sora-clear.webp", "width", 1200, 80
    yield "variants/sora-clear.jpg", "variants/sora-clear.avif", "width", 1200, 50
    yield "variants/cloud-tile.webp", "variants/cloud-tile.webp", None, None, 72
    yield "variants/cloud-tile.webp", "variants/cloud-tile.avif", None, None, 50
    for name in ("group", "setup", "reception", "prep", "staff", "core-card", "support-card"):
        for width in (1280, 640):
            yield f"2026/{name}.jpg", f"2026/{name}-{width}.webp", "width", width, 78
    for number in range(1, 13):
        path = f"retro/stamp-{number}.webp"
        yield path, path, "width", 460, 82
    for name in (
        "program", "venue", "attendee", "sponsor", "pr", "dev", "design", "local",
        "step-form", "step-slack", "step-onboarding",
    ):
        path = f"teams/{name}.webp"
        yield path, path, "longest", 480, 75
    for name in ("mikan-illust", "tealeaf-illust"):
        path = f"shizuoka/{name}.webp"
        yield path, path, "longest", 280, 80

    # Blog: 2026-10 venue visit. Portrait photos keep the width limit too.
    blog = "blog/2026-10-venue-visit"
    for name in (
        "rooftop", "sushi", "repubrew", "repubrew-beer", "exterior", "foyer-1f", "hall-a",
        "hall-b", "foyer-3f", "room-301", "room-401",
    ):
        for width in (1280, 640):
            yield f"{blog}/{name}.jpg", f"{blog}/{name}-{width}.webp", "width", width, 78
    for width in (1280, 640):
        yield f"{blog}/rooftop.jpg", f"{blog}/rooftop-{width}.avif", "width", width, 50
    # huddle.gif already has participants' names mosaicked. The original recording (never
    # committed) and the mosaic step live in ikedaosushi/pycon-jp-2027-design (proposals/tools/mosaic_huddle.py).
    # Animated: every frame is kept at its original size and delay.
    # Quality 25 keeps the 75 frames under 2 MB (30 gave 2.04 MB).
    yield f"{blog}/huddle.gif", f"{blog}/huddle.webp", None, None, 25
    # Shown instead of the animation under prefers-reduced-motion: reduce.
    yield f"{blog}/huddle.gif", f"{blog}/huddle-still.webp", None, None, 78


def main() -> None:
    originals = {}
    total = 0
    print("Original → WebP / AVIF (bytes; dimensions)", flush=True)
    for source_name, destination_name, axis, limit, quality in image_jobs():
        source = IMAGES / source_name
        destination = OUTPUT / destination_name
        with Image.open(source) as image:
            still_frame = STILL_FRAMES.get(destination_name)
            if still_frame is not None:
                image.seek(still_frame)
                image = image.convert("RGB")
            animated = getattr(image, "is_animated", False)
            if animated and (axis is not None or destination.suffix != ".webp"):
                raise ValueError(f"Animated images are only converted to WebP at their own size: {source_name}")
            if axis is not None:
                extent = {
                    "width": image.width,
                    "height": image.height,
                    "longest": max(image.size),
                }[axis]
                scale = min(1, limit / extent)
                size = tuple(round(dimension * scale) for dimension in image.size)
                if size != image.size:
                    image = image.resize(size, Image.Resampling.LANCZOS)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.suffix == ".avif":
                image.save(destination, "AVIF", quality=quality)
            elif destination.suffix != ".webp":
                raise ValueError(f"Unsupported output format: {destination_name}")
            elif animated:
                durations = []
                for frame in range(image.n_frames):
                    image.seek(frame)
                    durations.append(image.info["duration"])
                image.seek(0)
                image.save(
                    destination, "WEBP", quality=quality, method=6,
                    save_all=True, duration=durations, loop=0,
                )
                animated_size = destination.stat().st_size
                if animated_size > MAX_ANIMATED_BYTES:
                    raise ValueError(
                        f"Animated WebP is {animated_size:,} bytes, over {MAX_ANIMATED_BYTES:,}; "
                        f"lower its quality: {destination_name}"
                    )
            else:
                image.save(destination, "WEBP", quality=quality, method=6)
            dimensions = f"{image.width}x{image.height}"
        originals[source_name] = source.stat().st_size
        output_size = destination.stat().st_size
        total += output_size
        print(
            f"{source_name} ({originals[source_name]:,}) → "
            f"web/{destination_name} ({output_size:,}; {dimensions})",
            flush=True,
        )
    original_total = sum(originals.values())
    print(f"Originals (unique): {len(originals)} files, {original_total:,} bytes")
    print(f"WebP / AVIF (all sizes): {total:,} bytes ({100 * (1 - total / original_total):.1f}% smaller)")


if __name__ == "__main__":
    main()
