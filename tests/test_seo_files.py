"""
sitemap.xml + robots.txt smoke test.

Why: these two files are how Google decides what to crawl and how often. A
silent regression (wrong namespace, missing Sitemap: line, canonical drift
between robots + sitemap + index.html, an indexable page shipped to the
container but never listed in the sitemap) kills SEO discoverability without
a Lighthouse-visible signal. Stdlib only so `python tests/test_seo_files.py`
runs on any Python 3.11+ machine with zero setup.

Cross-checks:
  1. sitemap.xml parses as XML in the sitemap.org 0.9 namespace with >=1
     <url><loc>.
  2. robots.txt has a `Sitemap:` line.
  3. The robots.txt Sitemap URL matches sitemap.xml's canonical origin AND
     matches <link rel="canonical"> in index.html -- so a canonical change
     can never silently drift out of any of the three surfaces.
  4. Every <loc> URL, stripped of origin, resolves to a real on-disk file
     at repo root (drops the "url listed but git rm'd the file" regression
     class -- symmetric to test_assets.py for image bytes).
  5. Every top-level *.html file at repo root that is indexable
     (<meta name="robots" content="index,..."> AND has <link rel=canonical>)
     has a matching <loc> in the sitemap. Catches the exact class of drift
     that shipped accessibility.html indexable + COPY'd into the container
     but silently missing from the sitemap for ~1 tick.
  6. No duplicate <loc> entries.

Run:
    python tests/test_seo_files.py            # golden check on the real files
    python tests/test_seo_files.py --selftest # mutate baseline, expect each broken variant to fail
"""
from __future__ import annotations

import re
import sys
import tempfile
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
ROBOTS_META_RE = re.compile(
    r'<meta\s+name="robots"\s+content="(?P<content>[^"]+)"',
    re.IGNORECASE,
)

# 404.html is deliberately noindex + served via nginx error_page ... internal;
# so it must NEVER be in the sitemap. Any *.html file with `noindex` in its
# robots meta is excluded from coverage checks. Non-page assets never enter
# this test at all (they're not .html at repo root).
NOINDEX_TOKEN = "noindex"


def origin_of(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def _loc_to_repo_path(loc_url: str, canonical_origin: str, repo_root: Path) -> Path:
    """Strip origin off a sitemap <loc>, return the repo-root Path it points at.

    Clean-URL form (2026-07-19): the Cloudflare worker serves `/page` for
    `page.html` (and 307s the `.html` form), so canonical/sitemap URLs are
    extensionless. An extensionless path maps to `<path>.html` on disk unless
    a file with the literal name exists.
    """
    p = urlparse(loc_url)
    path = p.path or "/"
    if path == "/" or path == "":
        return repo_root / "index.html"
    rel = path.lstrip("/")
    target = repo_root / rel
    if target.exists() or "." in Path(rel).name:
        return target
    return repo_root / (rel + ".html")


def _indexable_html_files(repo_root: Path) -> list[Path]:
    """Return every top-level *.html file at repo root that is intended for crawl."""
    out: list[Path] = []
    for f in sorted(repo_root.glob("*.html")):
        text = f.read_text(encoding="utf-8", errors="ignore")
        m = ROBOTS_META_RE.search(text)
        if m and NOINDEX_TOKEN in m.group("content").lower():
            continue
        if not CANONICAL_RE.search(text):
            continue
        out.append(f)
    return out


def check_sitemap(path: Path) -> tuple[list[str], list[str]]:
    """Returns (errors, all_loc_urls_in_order)."""
    errors: list[str] = []
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        return [f"sitemap.xml is not valid XML: {exc}"], []

    root = tree.getroot()
    if root.tag != f"{{{SITEMAP_NS}}}urlset":
        errors.append(
            f"sitemap.xml root must be <urlset> in {SITEMAP_NS!r}, got {root.tag!r}"
        )

    urls = root.findall(f"{{{SITEMAP_NS}}}url")
    if not urls:
        errors.append("sitemap.xml has zero <url> entries")
        return errors, []

    locs: list[str] = []
    for i, url_el in enumerate(urls):
        loc_el = url_el.find(f"{{{SITEMAP_NS}}}loc")
        if loc_el is None or not (loc_el.text or "").strip():
            errors.append(f"sitemap.xml <url>[{i}] missing or empty <loc>")
            continue
        loc = loc_el.text.strip()
        if not loc.startswith("https://"):
            errors.append(f"sitemap.xml <url>[{i}] <loc> must be absolute https: {loc!r}")
        locs.append(loc)

    return errors, locs


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
) -> tuple[list[str], str | None]:
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

    return errors, canonical_origin


def check_no_duplicate_locs(locs: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    errors: list[str] = []
    for loc in locs:
        seen[loc] = seen.get(loc, 0) + 1
    for loc, n in seen.items():
        if n > 1:
            errors.append(f"sitemap.xml has duplicate <loc>: {loc!r} appears {n}x")
    return errors


def check_locs_on_disk(locs: list[str], canonical_origin: str | None, repo_root: Path) -> list[str]:
    errors: list[str] = []
    if canonical_origin is None:
        return errors
    for loc in locs:
        if origin_of(loc) != canonical_origin:
            # already flagged by check_canonical_agreement for the first entry;
            # for the rest, still flag so a mid-list drift is caught.
            errors.append(
                f"sitemap.xml <loc> {loc!r} origin does not match canonical {canonical_origin!r}"
            )
            continue
        target = _loc_to_repo_path(loc, canonical_origin, repo_root)
        if not target.exists():
            errors.append(
                f"sitemap.xml <loc> {loc!r} resolves to {target}, which does not exist on disk"
            )
    return errors


def check_sitemap_coverage(locs: list[str], canonical_origin: str | None, repo_root: Path) -> list[str]:
    """Every indexable top-level *.html file MUST be in the sitemap."""
    errors: list[str] = []
    if canonical_origin is None:
        return errors
    listed_paths = {
        _loc_to_repo_path(loc, canonical_origin, repo_root).resolve()
        for loc in locs
        if origin_of(loc) == canonical_origin
    }
    for f in _indexable_html_files(repo_root):
        if f.resolve() not in listed_paths:
            errors.append(
                f"sitemap.xml is missing an entry for indexable page {f.name!r} "
                f"(has <meta robots=index> + <link rel=canonical> but no matching <loc>)"
            )
    return errors


def run_all_checks(repo_root: Path) -> list[str]:
    sitemap = repo_root / "sitemap.xml"
    robots = repo_root / "robots.txt"
    index = repo_root / "index.html"

    for label, path in (("sitemap.xml", sitemap), ("robots.txt", robots), ("index.html", index)):
        if not path.exists():
            return [f"{label} not found at {path}"]

    sitemap_errors, locs = check_sitemap(sitemap)
    robots_errors, robots_sitemap = check_robots(robots)
    first_loc = locs[0] if locs else None
    agreement_errors, canonical_origin = check_canonical_agreement(
        first_loc, robots_sitemap, index.read_text(encoding="utf-8")
    )
    dupe_errors = check_no_duplicate_locs(locs)
    disk_errors = check_locs_on_disk(locs, canonical_origin, repo_root)
    coverage_errors = check_sitemap_coverage(locs, canonical_origin, repo_root)

    return sitemap_errors + robots_errors + agreement_errors + dupe_errors + disk_errors + coverage_errors


# ---------------------------------------------------------------------------
# Selftest scaffolding: build a minimal-but-realistic repo under a tempdir
# and mutate it N ways. Each mutation must be caught by run_all_checks.
# ---------------------------------------------------------------------------

BASELINE_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://big7construction.com/</loc>
    <lastmod>2026-07-11</lastmod>
  </url>
  <url>
    <loc>https://big7construction.com/home-repair.html</loc>
    <lastmod>2026-07-11</lastmod>
  </url>
  <url>
    <loc>https://big7construction.com/accessibility</loc>
    <lastmod>2026-07-11</lastmod>
  </url>
</urlset>
"""
# NOTE: the accessibility <loc> above is deliberately the clean extensionless
# form while home-repair keeps the .html form — the selftest baseline must
# exercise BOTH URL shapes through _loc_to_repo_path.

BASELINE_ROBOTS = """User-agent: *
Allow: /
Sitemap: https://big7construction.com/sitemap.xml
"""

BASELINE_INDEX = """<!doctype html>
<html lang="en"><head>
<link rel="canonical" href="https://big7construction.com/" />
<meta name="robots" content="index,follow" />
</head><body>Big 7</body></html>
"""

BASELINE_HOME_REPAIR = """<!doctype html>
<html lang="en"><head>
<link rel="canonical" href="https://big7construction.com/home-repair.html" />
<meta name="robots" content="index,follow" />
</head><body>Home repair lane</body></html>
"""

BASELINE_ACCESSIBILITY = """<!doctype html>
<html lang="en"><head>
<link rel="canonical" href="https://big7construction.com/accessibility.html" />
<meta name="robots" content="index,follow" />
</head><body>Accessibility statement</body></html>
"""

# 404 has noindex + no sitemap entry; must not trigger coverage failure.
BASELINE_NOT_FOUND = """<!doctype html>
<html lang="en"><head>
<link rel="canonical" href="https://big7construction.com/404" />
<meta name="robots" content="noindex" />
</head><body>Not found</body></html>
"""


def _write_baseline(root: Path) -> None:
    (root / "sitemap.xml").write_text(BASELINE_SITEMAP, encoding="utf-8")
    (root / "robots.txt").write_text(BASELINE_ROBOTS, encoding="utf-8")
    (root / "index.html").write_text(BASELINE_INDEX, encoding="utf-8")
    (root / "home-repair.html").write_text(BASELINE_HOME_REPAIR, encoding="utf-8")
    (root / "accessibility.html").write_text(BASELINE_ACCESSIBILITY, encoding="utf-8")
    (root / "404.html").write_text(BASELINE_NOT_FOUND, encoding="utf-8")


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_baseline(root)
        base_errors = run_all_checks(root)
        if base_errors:
            print("SELFTEST FAIL: baseline should PASS but got errors:")
            for e in base_errors:
                print(f"  - {e}")
            return 1
        print("SELFTEST OK  (baseline) PASS")

        mutations: list[tuple[str, str]] = []

        def add(label: str, replace_file: str, replace_with: str, expect_substr: str) -> None:
            mutations.append((label, replace_file))
            _write_baseline(root)
            (root / replace_file).write_text(replace_with, encoding="utf-8")
            errs = run_all_checks(root)
            if not any(expect_substr in e for e in errs):
                print(f"SELFTEST FAIL: mutation {label!r} not caught (expected substring {expect_substr!r})")
                print(f"  actual errors: {errs}")
                mutations[-1] = (label, "NOT_CAUGHT")
            else:
                print(f"SELFTEST OK  ({label}) caught")

        # 1) Sitemap missing an indexable page (the real gap this tick fixed).
        add(
            "coverage: indexable accessibility.html not in sitemap",
            "sitemap.xml",
            BASELINE_SITEMAP.replace(
                '  <url>\n    <loc>https://big7construction.com/accessibility</loc>\n    <lastmod>2026-07-11</lastmod>\n  </url>\n',
                "",
            ),
            "missing an entry for indexable page 'accessibility.html'",
        )

        # 2) Sitemap <loc> points at a file that doesn't exist on disk.
        add(
            "loc points at ghost file",
            "sitemap.xml",
            BASELINE_SITEMAP.replace("home-repair.html", "does-not-exist.html"),
            "does not exist on disk",
        )

        # 3) Duplicate <loc>.
        add(
            "duplicate <loc>",
            "sitemap.xml",
            BASELINE_SITEMAP.replace(
                "</urlset>",
                '  <url>\n    <loc>https://big7construction.com/home-repair.html</loc>\n  </url>\n</urlset>',
            ),
            "duplicate <loc>",
        )

        # 4) Canonical origin drift on index.html.
        add(
            "canonical origin drift index",
            "index.html",
            BASELINE_INDEX.replace("big7construction.com", "example.com"),
            "does not match index.html canonical origin",
        )

        # 5) Robots missing Sitemap: line.
        add(
            "robots missing Sitemap: line",
            "robots.txt",
            "User-agent: *\nAllow: /\n",
            "robots.txt is missing a Sitemap: line",
        )

        # 6) Robots missing User-agent line.
        add(
            "robots missing User-agent line",
            "robots.txt",
            "Sitemap: https://big7construction.com/sitemap.xml\n",
            "robots.txt is missing a User-agent line",
        )

        # 7) Sitemap loc uses http (not https).
        add(
            "loc not https",
            "sitemap.xml",
            BASELINE_SITEMAP.replace("https://big7construction.com/home-repair.html", "http://big7construction.com/home-repair.html"),
            "must be absolute https",
        )

        # 8) Sitemap XML malformed.
        add(
            "sitemap malformed XML",
            "sitemap.xml",
            "<?xml version=\"1.0\"?><urlset><url><loc>oops</url></urlset>",
            "not valid XML",
        )

        # 9) 404.html noindex + missing from sitemap: MUST NOT flag coverage failure.
        # (regression guard the wrong way -- baseline covers this positively but we also
        # confirm that adding another noindex page never triggers a false positive.)
        _write_baseline(root)
        (root / "hidden.html").write_text(BASELINE_NOT_FOUND, encoding="utf-8")
        errs = run_all_checks(root)
        if any("hidden.html" in e for e in errs):
            print("SELFTEST FAIL: noindex page 'hidden.html' triggered a false coverage failure")
            mutations.append(("noindex false-positive guard", "NOT_CAUGHT"))
        else:
            print("SELFTEST OK  (noindex page correctly excluded from coverage)")

        not_caught = [label for label, tag in mutations if tag == "NOT_CAUGHT"]
        if not_caught:
            print(f"SELFTEST: {len(not_caught)} mutation(s) not caught: {not_caught}")
            return 1
        print(f"SELFTEST: all mutations caught (+ noindex guard)")
        return 0


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return selftest()

    errors = run_all_checks(REPO_ROOT)
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    # For the summary line, re-derive the numbers cheaply.
    _, locs = check_sitemap(SITEMAP)
    _, robots_sitemap = check_robots(ROBOTS)
    print(
        f"OK: sitemap.xml valid ({len(locs)} url(s)); robots.txt Sitemap: line "
        f"points at {robots_sitemap}; matches index.html canonical; every <loc> "
        f"resolves to an on-disk file; every indexable *.html is listed."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
