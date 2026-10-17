#!/usr/bin/env python3
"""Build the public top page and selected drafts, using the standard library."""

import re
import shutil
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
PROPOSALS = ROOT / "proposals"
SITE = ROOT / "site"
DRAFT_PAGES = {
    "drafts-index.html": "index.html",
    "index.html": "initial.html",
    "a-kinetic.html": "a-kinetic.html",
    "b-warm.html": "b-warm.html",
    "c-suruga.html": "c-suruga.html",
    "a-variants.html": "a-variants.html",
    "a-chart.html": "a-chart.html",
    "a-hanga.html": "a-hanga.html",
    "a-tairyo.html": "a-tairyo.html",
    "logo-options.html": "logo-options.html",
}
FORBIDDEN_PATHS = ("lp10", "cp10", "ev10", "/ref/", "type-preview")
FORBIDDEN_PAGES = (
    "lp-compare.html", "lp-patterns.html", "campaign-lps.html", "events.html",
)

# Covers HTML src/srcset, CSS url(), and quoted JS paths. Keep ${...}
# together so whitespace in an interpolation does not truncate the reference.
IMAGE_REFERENCE = re.compile(
    r"(?<![\w/.-])(?:img|thumbs)/(?:\$\{[^}]*\}|[^\s\"'`()<>,$])+"
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
        if ".." in Path(path).parts or not path.startswith(("img/", "thumbs/")):
            raise ValueError(f"Image path escapes img/ or thumbs/: {reference}")
        paths.add(path)
    return paths


def validate_images(directory: Path, references: set[str]) -> None:
    for reference in sorted(references):
        image = directory / reference
        allowed = [directory / name for name in ("img", "thumbs")]
        if not any(image.resolve().is_relative_to(root.resolve()) for root in allowed):
            raise ValueError(f"Image path escapes img/ or thumbs/: {image}")
        if not image.is_file():
            raise FileNotFoundError(f"Referenced image does not exist: {image}")


class PageLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("a", "area"):
            self.links.extend(value for name, value in attrs if name == "href" and value)


def validate_public_paths(paths: set[str]) -> None:
    for path in sorted(paths):
        if any(token in f"/{path.lower()}" for token in FORBIDDEN_PATHS):
            raise ValueError(f"Forbidden public file: {path}")


def validate_draft_html(html: str, page: str) -> None:
    # Check the entire HTML so JS-generated links cannot bypass the check.
    decoded = unquote(unescape(html)).lower()
    for forbidden in FORBIDDEN_PAGES:
        if forbidden in decoded:
            raise ValueError(f"Forbidden comparison page in {page}: {forbidden}")


def validate_draft_links(directory: Path, html: str, page: str) -> None:
    parser = PageLinks()
    parser.feed(html)
    for href in parser.links:
        url = urlsplit(href)
        if url.scheme or url.netloc or not url.path:
            continue
        path = unquote(url.path)
        if path == "/":
            target = SITE / "index.html"
        else:
            target = SITE / path.lstrip("/") if path.startswith("/") else directory / path
            if not target.resolve().is_relative_to(directory.resolve()):
                raise ValueError(f"Link escapes drafts in {page}: {href}")
            if target.is_dir():
                target /= "index.html"
        if not target.is_file():
            raise FileNotFoundError(f"Missing link target in {page}: {href}")


def build_drafts() -> list[Path]:
    directory = SITE / "drafts"
    references = set()
    for source, destination in DRAFT_PAGES.items():
        html = (PROPOSALS / source).read_text(encoding="utf-8")
        validate_draft_html(html, source)
        references.update(image_references(html))
    expected = set(DRAFT_PAGES.values()) | references
    validate_public_paths(expected)
    validate_images(PROPOSALS, references)

    directory.mkdir()
    for source, destination in DRAFT_PAGES.items():
        shutil.copy2(PROPOSALS / source, directory / destination)
    for reference in sorted(references):
        destination = directory / reference
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROPOSALS / reference, destination)

    # Validate the copied HTML and assets, including every local navigation link.
    output_references = set()
    for page in DRAFT_PAGES.values():
        html = (directory / page).read_text(encoding="utf-8")
        validate_draft_html(html, page)
        validate_draft_links(directory, html, page)
        output_references.update(image_references(html))
    validate_images(directory, output_references)
    files = [path for path in directory.rglob("*") if path.is_file()]
    actual = {path.relative_to(directory).as_posix() for path in files}
    validate_public_paths(actual)
    if actual != set(DRAFT_PAGES.values()) | output_references:
        raise ValueError("Draft output files do not match the pages' references")
    return files


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
    draft_files = build_drafts()
    validate_public_paths({path.relative_to(SITE).as_posix() for path in files + draft_files})
    for label, group in (("Top (excluding drafts)", files), ("Drafts", draft_files)):
        size = sum(path.stat().st_size for path in group)
        print(f"{label}: {len(group)} files, {size:,} bytes")


if __name__ == "__main__":
    main()
