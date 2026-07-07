"""
sitemap.xml + robots.txt smoke test.

Why: these two files are how Google decides what to crawl and how often. A
silent regression (wrong namespace, missing Sitemap: line, canonical drift
between robots + sitemap + index.html) kills SEO discoverability without a
Lighthouse-visible signal. Stdlib only so `python tests/test_seo_files.py`
runs on any Python 3.11+ machine with zero setup.

Cross-checks:
  1. sitemap.xml parses as XML in the sitemap.org 0.9 namespace with >=1
     <url><loc>.
  2. robots.txt has a `Sitemap:` line.
  3. The robots.txt Sitemap URL matches sitemap.xml's canonical origin AND
     matches <link rel="canonical"> in index.html — so a canonical change
     can never silently drift out of any of the three surfaces.
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
SITEMAP = REPO_ROOT / "sitemap.xml"
ROBOTS = REPO_ROOT / "robots.txt"
INDEX = REPO_ROOT / "index.html"

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ROBOTS_SITEMAP_RE = re.compile(r"(?im)^\s*Sitemap:\s*(?P<url>\S+)\s*$")
CANONICAL_RE = re.compile(
    r'<link\s+rel="canonical"\s+href="(?P<url>[^"]+)"',
    re.IGNORECASE,
)


def origin_of(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def check_sitemap(path: Path) -> tuple[list[str], str | None]:
    """Returns (errors, first_loc_url_or_None)."""
    errors: list[str] = []
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        return [f"sitemap.xml is not valid XML: {exc}"], None

    root = tree.getroot()
    if root.tag != f"{{{SITEMAP_NS}}}urlset":
        errors.append(
            f"sitemap.xml root must be <urlset> in {SITEMAP_NS!r}, got {root.tag!r}"
        )

    urls = root.findall(f"{{{SITEMAP_NS}}}url")
    if not urls:
        errors.append("sitemap.xml has zero <url> entries")
        return errors, None

    first_loc: str | None = None
    for i, url_el in enumerate(urls):
        loc_el = url_el.find(f"{{{SITEMAP_NS}}}loc")
        if loc_el is None or not (loc_el.text or "").strip():
            errors.append(f"sitemap.xml <url>[{i}] missing or empty <loc>")
            continue
        loc = loc_el.text.strip()
        if not loc.startswith("https://"):
            errors.append(f"sitemap.xml <url>[{i}] <loc> must be absolute https: {loc!r}")
        if first_loc is None:
            first_loc = loc

    return errors, first_loc


def check_robots(path: Path) -> tuple[list[str], str | None]:
    """Returns (errors, first_sitemap_url_or_None)."""
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")

    if not re.search(r"(?im)^\s*User-agent:\s*\S+", text):
        errors.append("robots.txt is missing a User-agent line")

    sitemaps = ROBOTS_SITEMAP_RE.findall(text)
    if not sitemaps:
        errors.append("robots.txt is missing a Sitemap: line")
        return errors, None

    first = sitemaps[0]
    if not first.startswith("https://"):
        errors.append(f"robots.txt Sitemap URL must be absolute https: {first!r}")

    return errors, first


def check_canonical_agreement(
    sitemap_loc: str | None,
    robots_sitemap: str | None,
    index_html: str,
) -> list[str]:
    errors: list[str] = []

    m = CANONICAL_RE.search(index_html)
    if not m:
        errors.append("index.html is missing <link rel=\"canonical\" href=\"...\">")
        canonical_origin = None
    else:
        canonical_origin = origin_of(m.group("url"))

    if sitemap_loc and canonical_origin:
        if origin_of(sitemap_loc) != canonical_origin:
            errors.append(
                f"sitemap.xml first <loc> origin {origin_of(sitemap_loc)!r} "
                f"does not match index.html canonical origin {canonical_origin!r}"
            )

    if robots_sitemap and canonical_origin:
        if origin_of(robots_sitemap) != canonical_origin:
            errors.append(
                f"robots.txt Sitemap origin {origin_of(robots_sitemap)!r} "
                f"does not match index.html canonical origin {canonical_origin!r}"
            )

    if robots_sitemap and sitemap_loc:
        expected_sitemap_url = f"{origin_of(sitemap_loc)}/sitemap.xml"
        if robots_sitemap != expected_sitemap_url:
            errors.append(
                f"robots.txt Sitemap URL {robots_sitemap!r} does not equal "
                f"{expected_sitemap_url!r} (origin of sitemap.xml <loc> + /sitemap.xml)"
            )

    return errors


def main() -> int:
    for label, path in (("sitemap.xml", SITEMAP), ("robots.txt", ROBOTS), ("index.html", INDEX)):
        if not path.exists():
            print(f"FAIL: {label} not found at {path}", file=sys.stderr)
            return 1

    sitemap_errors, sitemap_loc = check_sitemap(SITEMAP)
    robots_errors, robots_sitemap = check_robots(ROBOTS)
    agreement_errors = check_canonical_agreement(
        sitemap_loc, robots_sitemap, INDEX.read_text(encoding="utf-8")
    )

    errors = sitemap_errors + robots_errors + agreement_errors
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(
        f"OK: sitemap.xml valid ({sitemap_loc}); robots.txt Sitemap: line "
        f"points at {robots_sitemap}; matches index.html canonical."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
