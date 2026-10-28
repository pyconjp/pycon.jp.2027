#!/usr/bin/env python3
"""Build the public top page, blog posts and selected drafts, using the standard library."""

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
BLOG_PAGES = {
    "blog-2026-10-venue-visit.html": "2026-10-venue-visit.html",
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
# Every src/srcset value and CSS url() must be one of the forms IMAGE_REFERENCE
# reads (img/..., thumbs/...), so /img/ or ../img/ cannot slip past the copy.
IMAGE_ATTRIBUTE = re.compile(r"""\b(src|srcset)\s*=\s*(["'])(.*?)\2""", re.DOTALL)
CSS_URL = re.compile(r"""url\(\s*(["']?)(.*?)\1\s*\)""", re.DOTALL)
# og:image / twitter:image on this host are copied like any other image.
SITE_HOST = "2027.pycon.jp"
META_IMAGE_KEYS = (
    "og:image", "og:image:url", "og:image:secure_url", "twitter:image", "twitter:image:src",
)
# Pages treats a site without a top-level 404.html as an SPA and answers
# unknown paths with index.html and 200, so publish a real 404 page.
NOT_FOUND_HTML = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ページが見つかりません | PyCon JP 2027</title>
<style>
body { margin: 0; padding: 4rem 1rem; background: #ffffff; color: #1a1a1a; font-family: system-ui, sans-serif; text-align: center; }
a { color: #1a4fa0; }
</style>
</head>
<body>
<main>
<h1>ページが見つかりません</h1>
<p><a href="/">トップへ戻る</a></p>
</main>
</body>
</html>
"""


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


def validate_image_reference_forms(html: str, page: str) -> None:
    values = []
    for match in IMAGE_ATTRIBUTE.finditer(html):
        attribute, value = match[1], unescape(match[3])
        if attribute == "srcset" and not value.lstrip().startswith("data:"):
            values.extend(candidate.split()[0] for candidate in value.split(",") if candidate.strip())
        else:
            values.append(value)
    values.extend(unescape(match[2]) for match in CSS_URL.finditer(html))
    for value in values:
        value = value.strip()
        url = urlsplit(value)
        # Absolute URLs, data: URIs and same-document SVG references (url(#id)).
        if url.scheme or url.netloc or value.startswith("#"):
            continue
        if not value.startswith(("img/", "thumbs/")):
            raise ValueError(f"Image reference in {page} is not under img/ or thumbs/: {value}")


class MetaImages(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        key = values.get("property") or values.get("name")
        if tag == "meta" and key in META_IMAGE_KEYS and values.get("content"):
            self.urls.append(values["content"])


def meta_image_references(html: str, directory: Path, page: str) -> set[str]:
    """Map og:image / twitter:image URLs on SITE_HOST to paths relative to directory."""
    parser = MetaImages()
    parser.feed(html)
    references = set()
    for content in parser.urls:
        url = urlsplit(content)
        if not url.netloc:
            raise ValueError(f"Meta image in {page} must be an absolute URL: {content}")
        if url.netloc != SITE_HOST:
            continue
        target = (SITE / unquote(url.path).lstrip("/")).resolve()
        if not target.is_relative_to(directory.resolve()):
            raise ValueError(
                f"Meta image in {page} is outside {directory.relative_to(ROOT)}: {content}"
            )
        references.add(target.relative_to(directory.resolve()).as_posix())
    return references


def page_references(html: str, directory: Path, page: str) -> set[str]:
    """Images the page in directory needs next to it, relative to directory."""
    validate_image_reference_forms(html, page)
    return image_references(html) | meta_image_references(html, directory, page)


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


class PageIds(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.ids.update(value for name, value in attrs if name == "id" and value)


def page_ids(html: str) -> set[str]:
    parser = PageIds()
    parser.feed(html)
    return parser.ids


def validate_public_paths(paths: set[str]) -> None:
    for path in sorted(paths):
        if any(token in f"/{path.lower()}" for token in FORBIDDEN_PATHS):
            raise ValueError(f"Forbidden public file: {path}")


def validate_no_comparison_pages(html: str, page: str) -> None:
    # Check the entire HTML so JS-generated links cannot bypass the check.
    decoded = unquote(unescape(html)).lower()
    for forbidden in FORBIDDEN_PAGES:
        if forbidden in decoded:
            raise ValueError(f"Forbidden comparison page in {page}: {forbidden}")


def validate_local_links(directory: Path, html: str, page: str, boundary: Path) -> None:
    """Require every local link of a page in directory to reach a file within boundary.

    The site root "/" is always allowed, so drafts can link back to the top page.
    A fragment (#join) must be an id in the target HTML, or in this page for "#id".
    """
    parser = PageLinks()
    parser.feed(html)
    for href in parser.links:
        url = urlsplit(href)
        if url.scheme or url.netloc:
            continue
        fragment = unquote(url.fragment)
        if not url.path:
            if fragment and fragment not in page_ids(html):
                raise ValueError(f"Missing link fragment in {page}: {href}")
            continue
        path = unquote(url.path)
        if path == "/":
            target = SITE / "index.html"
        else:
            target = SITE / path.lstrip("/") if path.startswith("/") else directory / path
            if not target.resolve().is_relative_to(boundary.resolve()):
                raise ValueError(f"Link escapes {boundary.relative_to(ROOT)} in {page}: {href}")
            if target.is_dir():
                target /= "index.html"
        if not target.is_file():
            raise FileNotFoundError(f"Missing link target in {page}: {href}")
        if fragment:
            if target.suffix != ".html":
                raise ValueError(f"Cannot check a fragment of a non-HTML target in {page}: {href}")
            if fragment not in page_ids(target.read_text(encoding="utf-8")):
                raise ValueError(f"Missing link fragment in {page}: {href}")


def build_pages(directory: Path, pages: dict[str, str], link_boundary: Path) -> list[Path]:
    """Publish pages in directory with their own copy of every image they reference.

    Local links must stay within link_boundary. Pages that link to the top
    page must be built after it.
    """
    references = set()
    for source in pages:
        html = (PROPOSALS / source).read_text(encoding="utf-8")
        validate_no_comparison_pages(html, source)
        references.update(page_references(html, directory, source))
    validate_public_paths(set(pages.values()) | references)
    validate_images(PROPOSALS, references)

    directory.mkdir()
    for source, destination in pages.items():
        shutil.copy2(PROPOSALS / source, directory / destination)
    for reference in sorted(references):
        destination = directory / reference
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROPOSALS / reference, destination)

    # Validate the copied HTML and assets, including every local navigation link.
    output_references = set()
    for page in pages.values():
        html = (directory / page).read_text(encoding="utf-8")
        validate_no_comparison_pages(html, page)
        validate_local_links(directory, html, page, boundary=link_boundary)
        output_references.update(page_references(html, directory, page))
    validate_images(directory, output_references)
    files = [path for path in directory.rglob("*") if path.is_file()]
    actual = {path.relative_to(directory).as_posix() for path in files}
    validate_public_paths(actual)
    if actual != set(pages.values()) | output_references:
        raise ValueError(
            f"Output files in {directory.relative_to(ROOT)} do not match the pages' references"
        )
    return files


def main() -> None:
    if SITE.is_symlink():
        raise ValueError(f"Output directory must not be a symlink: {SITE}")
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()

    source = PROPOSALS / "a-sora.html"
    references = page_references(source.read_text(encoding="utf-8"), SITE, source.name)
    validate_images(PROPOSALS, references)
    shutil.copy2(source, SITE / "index.html")
    (SITE / "_headers").write_text(
        "/img/*\n"
        "  Cache-Control: public, max-age=86400, stale-while-revalidate=604800\n"
        "/drafts/img/*\n"
        "  Cache-Control: public, max-age=86400, stale-while-revalidate=604800\n"
        "/blog/img/*\n"
        "  Cache-Control: public, max-age=86400, stale-while-revalidate=604800\n",
        encoding="utf-8",
    )
    (SITE / "404.html").write_text(NOT_FOUND_HTML, encoding="utf-8")
    for reference in sorted(references):
        destination = SITE / reference
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROPOSALS / reference, destination)

    # Re-read the actual output and verify every expanded reference within site/.
    output_references = page_references(
        (SITE / "index.html").read_text(encoding="utf-8"), SITE, "index.html"
    )
    validate_images(SITE, output_references)
    files = [path for path in SITE.rglob("*") if path.is_file()]
    expected = {"index.html", "404.html", "_headers"} | output_references
    if {path.relative_to(SITE).as_posix() for path in files} != expected:
        raise ValueError("Output files do not match the page's references")
    draft_files = build_pages(SITE / "drafts", DRAFT_PAGES, link_boundary=SITE / "drafts")
    # Posts link back to the top page (../, ../#join), so they may link anywhere in site/.
    blog_files = build_pages(SITE / "blog", BLOG_PAGES, link_boundary=SITE)
    # The top page links to blog posts, so check its links once they exist.
    validate_local_links(SITE, (SITE / "index.html").read_text(encoding="utf-8"), "index.html", boundary=SITE)
    validate_public_paths(
        {path.relative_to(SITE).as_posix() for path in files + draft_files + blog_files}
    )
    for label, group in (
        ("Top (excluding drafts and blog)", files), ("Drafts", draft_files), ("Blog", blog_files),
    ):
        size = sum(path.stat().st_size for path in group)
        print(f"{label}: {len(group)} files, {size:,} bytes")


if __name__ == "__main__":
    main()
