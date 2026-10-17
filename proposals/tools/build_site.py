#!/usr/bin/env python3
"""Build only a-sora.html and its referenced images, using the standard library."""

import re
import shutil
from html import unescape
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
PROPOSALS = ROOT / "proposals"
SITE = ROOT / "site"

# Covers HTML src/srcset, CSS url(), and quoted JS paths. Keep ${...}
# together so whitespace in an interpolation does not truncate the reference.
IMAGE_REFERENCE = re.compile(
    r"(?<![\w/.-])img/(?:\$\{[^}]*\}|[^\s\"'`()<>,$])+"
)
ARRAY_FROM = re.compile(
    r"Array\.from\(\s*\{\s*length:\s*(\d+)\s*\}\s*,\s*"
    r"\(\s*_\s*,\s*(\w+)\s*\)\s*=>\s*\{(.*?)\}\s*\)",
    re.DOTALL,
)
INTERPOLATION = re.compile(r"\$\{([^}]*)\}")


def image_references(html: str) -> set[str]:
    """Expand the page's Array.from templates; reject unknown dynamic paths.

    a-sora's stampPool uses length: 12 and stamp-${index + 1}.webp.
    Read the bound and index name from JS instead of globbing stamp-* (which
    could publish unused files or conceal a missing numbered image).
    This intentionally supports only integer index expressions, not arbitrary JS.
    """
    expanded = set()

    def expand_array(match: re.Match) -> str:
        length, variable, body = match.groups()

        def expand_reference(reference: re.Match) -> str:
            template = reference.group()
            if "${" not in template:
                return template
            for index in range(int(length)):

                def evaluate(expression: re.Match) -> str:
                    arithmetic = re.fullmatch(
                        rf"\s*{re.escape(variable)}\s*(?:([+-])\s*(\d+))?\s*",
                        expression[1],
                    )
                    if arithmetic is None:
                        raise ValueError(f"Unsupported image template: {template}")
                    sign, amount = arithmetic.groups()
                    offset = int(amount or 0) * (-1 if sign == "-" else 1)
                    return str(index + offset)

                expanded.add(INTERPOLATION.sub(evaluate, template))
            return ""

        return IMAGE_REFERENCE.sub(expand_reference, body)

    static_html = ARRAY_FROM.sub(expand_array, html)
    references = expanded | set(IMAGE_REFERENCE.findall(static_html))
    paths = set()
    for reference in references:
        if "${" in reference:
            raise ValueError(f"Unsupported image template: {reference}")
        path = unquote(urlsplit(unescape(reference)).path)
        if ".." in Path(path).parts or not path.startswith("img/"):
            raise ValueError(f"Image path escapes img/: {reference}")
        paths.add(path)
    return paths


def validate_images(directory: Path, references: set[str]) -> None:
    for reference in sorted(references):
        image = directory / reference
        if not image.resolve().is_relative_to((directory / "img").resolve()):
            raise ValueError(f"Image path escapes img/: {image}")
        if not image.is_file():
            raise FileNotFoundError(f"Referenced image does not exist: {image}")


def main() -> None:
    if SITE.is_symlink():
        raise ValueError(f"Output directory must not be a symlink: {SITE}")
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()

    source = PROPOSALS / "a-sora.html"
    references = image_references(source.read_text(encoding="utf-8"))
    validate_images(PROPOSALS, references)
    shutil.copy2(source, SITE / "index.html")
    for reference in sorted(references):
        destination = SITE / reference
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROPOSALS / reference, destination)

    # Re-read the actual output and verify every expanded reference within site/.
    output_references = image_references((SITE / "index.html").read_text(encoding="utf-8"))
    validate_images(SITE, output_references)
    files = [path for path in SITE.rglob("*") if path.is_file()]
    expected = {"index.html"} | output_references
    if {path.relative_to(SITE).as_posix() for path in files} != expected:
        raise ValueError("Output files do not match the page's references")
    size = sum(path.stat().st_size for path in files)
    print(f"Copied {len(files)} files ({len(output_references)} images): {size:,} bytes")


if __name__ == "__main__":
    main()
