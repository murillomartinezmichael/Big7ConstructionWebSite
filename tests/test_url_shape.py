"""
Canonical URL-shape contract — one lock for the whole `.html` -> clean-path arc.

Why this exists
---------------
The site has ONE canonical URL shape:

    https://big7construction.com/<page>        (apex, https, no `www`, no `.html`)

Three separate facts make that shape load-bearing rather than cosmetic:

  1. Cloudflare Workers static assets (host of record since 2026-07-17) serves
     pages extensionless and **307s the `.html` form** — verified live
     2026-08-03. So a `.html` URL anywhere costs a redirect hop, and a `.html`
     canonical points at a URL that redirects away from itself.
  2. `www` was **intentionally decommissioned** (Mike's call, 2026-07-17) —
     apex is the sole host. A `www.` URL in shipped markup is a dead host.
  3. The SEO-signal half of this arc shipped 2026-07-19 (`81d9f4d`) and the
     internal-link half shipped 2026-08-03. Both halves were previously
     guarded only by per-surface tests that each knew about one file, so the
     shape could drift back one surface at a time without any single test
     noticing.

The existing suites lock their own surfaces (test_seo_files: sitemap/robots;
test_og_twitter: canonical<->og:url agreement; test_breadcrumbs / test_jsonld /
test_offer_catalog / test_service_schema: structured data; test_lane_nav /
test_anchors / test_404_lane_recovery: navigation hrefs). NONE of them assert
the *shape* itself across all surfaces at once. This test is that assertion,
so the arc cannot be half-reverted.

Contract asserted
-----------------
  1. Every `<link rel="canonical">` and `og:url` on every root *.html is
     apex-origin, https, and carries no `.html` extension.
  2. Every sitemap.xml `<loc>` is apex-origin, https, no `.html`.
  3. Every absolute big7construction.com URL inside a JSON-LD block is
     apex-origin, https, no `.html`.
  4. Every root-relative internal `href="/..."` in every root *.html points at
     a clean path — no `href="/<page>.html"` (each one would cost a 307 hop).
  5. `_redirects` (Cloudflare) targets are clean paths — a `.html` target
     chains 301 -> 307 -> 200, which is what this arc found live on
     `/home-repair.html` and fixed.
  6. nginx.conf (the Railway fallback) can actually SERVE the clean paths:
     `location /` try_files includes `$uri.html`, and still ends in `=404`.
     Its `return 301` targets are clean too, so the fallback matches CF.
  7. The literal string `www.big7construction.com` appears nowhere in any
     shipped file — `www` is decommissioned, not redirected.

Python 3.11+ stdlib only (`re`, `pathlib`, `sys`). No pip, no network.

Run:
    python tests/test_url_shape.py            # golden check on the real repo
    python tests/test_url_shape.py --selftest # mutate a baseline, expect each to fail
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

APEX = "https://big7construction.com"
WWW_HOST = "www.big7construction.com"

# Pages CF serves extensionless. `index.html` is excluded from the href rule
# because the canonical home form is `/` (never `/index.html`), and `404.html`
# is served internally by error_page — it is never linked.
CLEAN_PAGES = (
    "commercial-industrial",
    "residential-construction",
    "south-fulton-distribution",
    "accessibility",
)

CANONICAL_RE = re.compile(
    r'<link\b[^>]*\brel=["\']canonical["\'][^>]*\bhref=["\'](?P<url>[^"\']+)["\']',
    re.IGNORECASE,
)
OG_URL_RE = re.compile(
    r'<meta\b[^>]*\bproperty=["\']og:url["\'][^>]*\bcontent=["\'](?P<url>[^"\']+)["\']',
    re.IGNORECASE,
)
SITEMAP_LOC_RE = re.compile(r"<loc>\s*(?P<url>[^<\s]+)\s*</loc>", re.IGNORECASE)
JSONLD_BLOCK_RE = re.compile(
    r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(?P<body>.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
# Absolute big7construction.com URLs inside JSON-LD (any scheme/host spelling).
JSONLD_URL_RE = re.compile(r'["\'](?P<url>https?://[^"\']*big7construction\.com[^"\']*)["\']')
# Root-relative hrefs only — external links and fragments are out of scope.
HREF_ROOT_RE = re.compile(r'href=["\'](?P<href>/[^"\'#?]*)(?P<rest>[^"\']*)["\']', re.IGNORECASE)
# `_redirects` line: <from> <to> <status>
REDIRECT_LINE_RE = re.compile(r"^\s*(?P<src>/\S+)\s+(?P<dst>\S+)\s+(?P<code>\d{3})\s*$")
NGINX_RETURN_RE = re.compile(r"return\s+30[12]\s+(?P<target>\S+?);")


def _url_shape_errors(url: str, where: str) -> list[str]:
    """Shared shape rules for any absolute site URL: apex, https, no `.html`."""
    errors: list[str] = []
    if WWW_HOST in url:
        errors.append(
            f"{where}: {url!r} uses the decommissioned `www` host — apex "
            f"({APEX}) is the sole host since 2026-07-17, so this URL is dead"
        )
    elif url.startswith("http://"):
        errors.append(f"{where}: {url!r} is http:// — must be https")
    elif not url.startswith(APEX):
        errors.append(f"{where}: {url!r} does not start with the apex origin {APEX}")
    if re.search(r"\.html(?:[?#]|$)", url):
        errors.append(
            f"{where}: {url!r} carries a `.html` extension — the live worker "
            f"307s that form, so this URL redirects away from itself"
        )
    return errors


def check_page_urls(name: str, html: str) -> list[str]:
    """Contract 1 + 3 — canonical/og:url and JSON-LD URLs on one page."""
    errors: list[str] = []
    for label, rx in (("canonical", CANONICAL_RE), ("og:url", OG_URL_RE)):
        for m in rx.finditer(html):
            errors.extend(_url_shape_errors(m.group("url"), f"{name} <{label}>"))
    for block in JSONLD_BLOCK_RE.finditer(html):
        for m in JSONLD_URL_RE.finditer(block.group("body")):
            errors.extend(_url_shape_errors(m.group("url"), f"{name} JSON-LD"))
    return errors


def check_internal_hrefs(name: str, html: str) -> list[str]:
    """Contract 4 — no root-relative href points at a redirecting `.html`."""
    errors: list[str] = []
    seen: set[str] = set()
    for m in HREF_ROOT_RE.finditer(html):
        href = m.group("href")
        stem = href.rstrip("/").lstrip("/")
        if not stem.endswith(".html"):
            continue
        page = stem[: -len(".html")]
        if page not in CLEAN_PAGES or href in seen:
            continue
        seen.add(href)
        errors.append(
            f"{name}: internal href={href!r} uses the `.html` form — the live "
            f"worker 307s it, so every click pays an extra hop; link '/{page}'"
        )
    return errors


def check_sitemap(text: str) -> list[str]:
    """Contract 2."""
    errors: list[str] = []
    locs = [m.group("url") for m in SITEMAP_LOC_RE.finditer(text)]
    if not locs:
        return ["sitemap.xml: no <loc> entries found — sanity check tripped"]
    for loc in locs:
        errors.extend(_url_shape_errors(loc, "sitemap.xml <loc>"))
    return errors


def check_redirects(text: str) -> list[str]:
    """Contract 5 — a `.html` redirect TARGET chains 301 -> 307 -> 200."""
    errors: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = REDIRECT_LINE_RE.match(line)
        if not m:
            errors.append(f"_redirects: unparseable rule {line!r}")
            continue
        dst = m.group("dst")
        if re.search(r"\.html(?:[?#]|$)", dst):
            errors.append(
                f"_redirects: rule {m.group('src')!r} targets {dst!r} — the "
                f"`.html` target itself 307s, so this chains 301 -> 307 -> 200; "
                f"point it at the clean path"
            )
        if WWW_HOST in dst:
            errors.append(f"_redirects: rule targets the decommissioned www host: {dst!r}")
    return errors


def check_nginx(text: str) -> list[str]:
    """Contract 6 — the fallback can serve clean paths and mirrors CF."""
    errors: list[str] = []
    root_loc = re.search(r"location\s+/\s*\{(?P<body>.*?)\n    \}", text, re.DOTALL)
    if root_loc is None:
        errors.append("nginx.conf: no `location / { ... }` block found")
    else:
        tf = re.search(r"try_files\s+(?P<body>[^;]+);", root_loc.group("body"))
        if tf is None:
            errors.append("nginx.conf: `location /` has no try_files directive")
        else:
            body = tf.group("body").strip()
            if "$uri.html" not in body:
                errors.append(
                    f"nginx.conf: try_files is {body!r} — missing `$uri.html`, so "
                    f"the Railway fallback would 404 on every clean-path link "
                    f"(the entire site's internal navigation)"
                )
            if not re.search(r"=\s*404\s*$", body):
                errors.append(
                    f"nginx.conf: try_files is {body!r} — must still end in `=404` "
                    f"so typos stay real 404s (see test_nginx_headers contract 6)"
                )
    for m in NGINX_RETURN_RE.finditer(text):
        target = m.group("target")
        if re.search(r"\.html(?:[?#]|$)", target):
            errors.append(
                f"nginx.conf: `return 301 {target}` uses the `.html` form — the "
                f"fallback should mirror the clean CF target"
            )
    return errors


def check_no_www(repo_root: Path) -> list[str]:
    """Contract 7 — `www` is decommissioned, so it must appear in no shipped file."""
    errors: list[str] = []
    shipped = sorted(repo_root.glob("*.html"))
    for extra in ("sitemap.xml", "robots.txt", "_redirects", "_headers", "big7.js", "nginx.conf"):
        p = repo_root / extra
        if p.is_file():
            shipped.append(p)
    for f in shipped:
        text = f.read_text(encoding="utf-8", errors="replace")
        if WWW_HOST in text:
            errors.append(
                f"{f.name}: contains {WWW_HOST!r} — `www` was decommissioned "
                f"(not redirected) on 2026-07-17; that hostname does not resolve"
            )
    return errors


def run_all_checks(repo_root: Path) -> list[str]:
    errors: list[str] = []

    html_files = sorted(repo_root.glob("*.html"))
    if not html_files:
        return ["no *.html files at repo root — sanity check tripped"]
    for f in html_files:
        html = f.read_text(encoding="utf-8", errors="replace")
        errors.extend(check_page_urls(f.name, html))
        errors.extend(check_internal_hrefs(f.name, html))

    sitemap = repo_root / "sitemap.xml"
    if not sitemap.is_file():
        errors.append("sitemap.xml missing")
    else:
        errors.extend(check_sitemap(sitemap.read_text(encoding="utf-8")))

    redirects = repo_root / "_redirects"
    if not redirects.is_file():
        errors.append("_redirects missing")
    else:
        errors.extend(check_redirects(redirects.read_text(encoding="utf-8")))

    nginx = repo_root / "nginx.conf"
    if not nginx.is_file():
        errors.append("nginx.conf missing")
    else:
        errors.extend(check_nginx(nginx.read_text(encoding="utf-8")))

    errors.extend(check_no_www(repo_root))
    return errors


# ---------------------------------------------------------------------------
# Selftest — build a minimal-but-real baseline repo in a temp dir, prove it
# PASSes, then mutate it one surface at a time and require each break to be
# caught. Matches the house pattern (test_seo_files / test_lane_nav / ...).
# ---------------------------------------------------------------------------

BASELINE_PAGE = """<!doctype html>
<html lang="en"><head>
  <link rel="canonical" href="https://big7construction.com/commercial-industrial" />
  <meta property="og:url" content="https://big7construction.com/commercial-industrial" />
  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"Service",
   "url":"https://big7construction.com/commercial-industrial",
   "provider":{"@type":"GeneralContractor","url":"https://big7construction.com/"}}
  </script>
</head><body>
  <nav><a href="/residential-construction">Residential</a>
       <a href="/south-fulton-distribution">Case study</a>
       <a href="/accessibility">Accessibility</a>
       <a href="/">Home</a></nav>
</body></html>
"""

BASELINE_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://big7construction.com/</loc></url>
  <url><loc>https://big7construction.com/commercial-industrial</loc></url>
</urlset>
"""

BASELINE_REDIRECTS = """# comment line
/home-repair.html /residential-construction 301
/home-repair /residential-construction 301
"""

BASELINE_NGINX = """server {
    listen 8080;
    location / {
        try_files $uri $uri.html $uri/ =404;
    }
    location = /home-repair.html {
        return 301 /residential-construction#home-repair;
    }
}
"""


def _write_baseline(root: Path) -> None:
    for f in root.glob("*"):
        if f.is_file():
            f.unlink()
    (root / "commercial-industrial.html").write_text(BASELINE_PAGE, encoding="utf-8")
    (root / "sitemap.xml").write_text(BASELINE_SITEMAP, encoding="utf-8")
    (root / "_redirects").write_text(BASELINE_REDIRECTS, encoding="utf-8")
    (root / "nginx.conf").write_text(BASELINE_NGINX, encoding="utf-8")


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

        not_caught: list[str] = []

        def add(label: str, filename: str, content: str, expect: str) -> None:
            _write_baseline(root)
            (root / filename).write_text(content, encoding="utf-8")
            errs = run_all_checks(root)
            if not any(expect in e for e in errs):
                print(f"SELFTEST FAIL: mutation {label!r} not caught (expected {expect!r})")
                print(f"  actual errors: {errs}")
                not_caught.append(label)
            else:
                print(f"SELFTEST OK  ({label}) caught")

        add(
            "canonical regains .html",
            "commercial-industrial.html",
            BASELINE_PAGE.replace(
                'href="https://big7construction.com/commercial-industrial"',
                'href="https://big7construction.com/commercial-industrial.html"',
            ),
            "redirects away from itself",
        )
        add(
            "og:url reverts to www host",
            "commercial-industrial.html",
            BASELINE_PAGE.replace(
                'content="https://big7construction.com/commercial-industrial"',
                'content="https://www.big7construction.com/commercial-industrial"',
            ),
            "decommissioned `www` host",
        )
        add(
            "JSON-LD url regains .html",
            "commercial-industrial.html",
            BASELINE_PAGE.replace(
                '"url":"https://big7construction.com/commercial-industrial"',
                '"url":"https://big7construction.com/commercial-industrial.html"',
            ),
            "JSON-LD",
        )
        add(
            "internal href regains .html (extra 307 hop)",
            "commercial-industrial.html",
            BASELINE_PAGE.replace(
                'href="/residential-construction"', 'href="/residential-construction.html"'
            ),
            "pays an extra hop",
        )
        add(
            "sitemap loc regains .html",
            "sitemap.xml",
            BASELINE_SITEMAP.replace(
                "/commercial-industrial<", "/commercial-industrial.html<"
            ),
            "sitemap.xml <loc>",
        )
        add(
            "sitemap loc reverts to http",
            "sitemap.xml",
            BASELINE_SITEMAP.replace("https://big7construction.com/c", "http://big7construction.com/c"),
            "must be https",
        )
        add(
            "_redirects target regains .html (301 -> 307 chain)",
            "_redirects",
            BASELINE_REDIRECTS.replace(
                "/home-repair.html /residential-construction 301",
                "/home-repair.html /residential-construction.html 301",
            ),
            "301 -> 307 -> 200",
        )
        add(
            "nginx try_files loses $uri.html (fallback 404s every link)",
            "nginx.conf",
            BASELINE_NGINX.replace("try_files $uri $uri.html $uri/ =404;", "try_files $uri $uri/ =404;"),
            "missing `$uri.html`",
        )
        add(
            "nginx try_files stops ending in =404",
            "nginx.conf",
            BASELINE_NGINX.replace(
                "try_files $uri $uri.html $uri/ =404;", "try_files $uri $uri.html /index.html;"
            ),
            "must still end in `=404`",
        )
        add(
            "nginx 301 target regains .html",
            "nginx.conf",
            BASELINE_NGINX.replace(
                "return 301 /residential-construction#home-repair;",
                "return 301 /residential-construction.html#home-repair;",
            ),
            "should mirror the clean CF target",
        )

        if not_caught:
            print(f"SELFTEST: {len(not_caught)} mutation(s) not caught: {not_caught}")
            return 1
        print("SELFTEST: all 10 mutations caught")
        return 0


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return selftest()

    errors = run_all_checks(REPO_ROOT)
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    pages = len(list(REPO_ROOT.glob("*.html")))
    print(
        f"OK: one canonical URL shape across every surface — apex origin, https, "
        f"no `www`, no `.html`. Verified on {pages} root pages (canonical/og:url/"
        f"JSON-LD/internal hrefs), sitemap.xml, _redirects, and the nginx fallback."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
