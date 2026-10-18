#!/usr/bin/env python3
"""Generate WebP and AVIF assets without changing originals.

Run with: python3 proposals/tools/optimize_images.py
Requires Pillow with WebP and AVIF support. Every run starts from the original images.
"""

from pathlib import Path

from PIL import Image


IMAGES = Path(__file__).resolve().parents[1] / "img"
OUTPUT = IMAGES / "web"


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

    # Drafts reuse the existing 2026 photos above; only crowd needs new sizes.
    for width in (1280, 640):
        yield "2026/crowd.jpg", f"2026/crowd-{width}.webp", "width", width, 78
    for name in (
        "variants/tairyo-bg", "b-hero", "variants/hanga-bg", "c-hero", "b-team",
        "logo/retro", "logo/wave", "logo/brush",
    ):
        yield f"{name}.jpg", f"{name}.webp", "width", 1376, 78
    for name in ("tairyo", "hanga", "chart"):
        for device in ("pc", "sp"):
            path = f"variants/shots/a-{name}-{device}"
            yield f"{path}.jpg", f"{path}.webp", None, None, 80
    for name in ("a-kinetic", "b-warm", "c-suruga"):
        yield f"../thumbs/{name}.jpg", f"thumbs/{name}.webp", None, None, 80
    # Keep the transparent lockup separate from the full brush.jpg logo option.
    yield "logo/brush.png", "logo/brush-transparent.webp", None, None, 88


def main() -> None:
    originals = {}
    total = 0
    print("Original → WebP / AVIF (bytes; dimensions)", flush=True)
    for source_name, destination_name, axis, limit, quality in image_jobs():
        source = IMAGES / source_name
        destination = OUTPUT / destination_name
        with Image.open(source) as image:
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
