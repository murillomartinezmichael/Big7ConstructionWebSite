"""
Canonical URL-shape contract — one lock for the whole `.html` -> clean-path arc.

Why this exists
---------------
The site has ONE canonical URL shape:

    https://big7construction.com/<page>        (apex, https, no `www`, no `.html`)

Three separate facts make that shape load-bearing rather than cosmetic:

  1. Cloudflare Workers static assets (host of record since 2026-07-17) serves
     pages extensionless and redirects the `.html` form away — verified live
     2026-08-03. So a `.html` URL anywhere costs a redirect hop, and a `.html`
     canonical points at a URL that redirects away from itself. As of
     2026-08-12 that hop is a permanent 301 (contract 8 below); before then it
     was CF's built-in `html_handling` **307**, which is a temporary signal.
  2. `www` was slated for decommission (Mike's call, 2026-07-17); observed
     2026-08-07 it still serves a byte-identical duplicate of apex (disposition
     pending in PENDING_MANUAL.md). Either way apex is the sole canonical
     host, so a `www.` URL in shipped markup is wrong.
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
  6. nginx.conf (the Railway fallback) SERVES the clean paths *and* redirects
     the `.html` forms exactly like Cloudflare does. Both halves matter:
       a. `location /` try_files includes `$uri.html` and still ends in `=404`
          — that is the only reason a clean path resolves at all on the
          fallback; without it every internal link 404s.
       b. Every source in the shared redirect map (see `expected_redirect_map`)
          has an EXACT-match `location = <src>` block issuing `return 301` to
          the same clean destination `_redirects` uses, and the two stacks'
          redirect maps are compared to each other key by key, so neither can
          drift away from the other.
       c. Every nginx redirect carries `$is_args$args`. nginx's `return` sends
          exactly the URL written and DROPS the query string, where Cloudflare
          preserves it — so without the suffix the two stacks agree on the page
          but disagree on the money path: `?intent=` / `?utm_*` would die on
          the hop and the intake form would land unprefilled and unattributed.
     Until 2026-08-12 only (a) was asserted. try_files' `$uri` arm means
     `/commercial-industrial.html` was served **200** on the fallback while
     Cloudflare 301'd it — i.e. a failover silently restored the duplicate-
     content shape this whole arc exists to remove, and no test objected.
     Found by a real `make test-container` run, not by reading.
     nginx precedence note: an exact-match (`location = /x`) always wins over
     the `location /` prefix match no matter where it sits in the file
     (nginx matches by specificity, unlike Cloudflare's `_redirects`, which
     applies the FIRST matching line). The test therefore requires the `=`
     form rather than trusting file order.
  7. The literal string `www.big7construction.com` appears nowhere in any
     shipped file — apex is the sole canonical host (www's live disposition
     is a pending dashboard decision, not a markup concern).
  8. Every page that ships as a root `*.html` file carries an explicit
     **301** rule in `_redirects` sending its `.html` form to its clean path
     (`/index.html` -> `/`). Without the explicit rule CF falls back to
     `html_handling`, which answers **307 Temporary** — Google keeps the
     `.html` URL as a live index candidate instead of consolidating it, and
     legacy inbound link equity is not fully passed. Also asserted: no rule's
     target is another rule's source (that is a redirect CHAIN), no rule
     points at itself (that is a LOOP), and no source is declared twice
     (Cloudflare applies the FIRST match, so a duplicate silently overrides).
  9. `wrangler.jsonc` keeps an `html_handling` mode under which the clean
     paths still serve 200 **directly**. Contract 8's rules are only one hop
     because their targets don't redirect again — and that is decided in the
     worker config, not in `_redirects`. `force-trailing-slash` would make
     every `.html` 301 a two-hop chain and turn every submitted sitemap URL
     into a redirect; `none` would 404 every canonical and internal link.

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

# nginx `return` emits exactly the URL it is given — the request's query
# string is NOT carried over (unlike Cloudflare's `_redirects`, which does).
# `$is_args$args` re-appends it, and the money-path prefill in big7.js
# (`?intent=`, `?utm_*`) depends on surviving the hop.
QUERY_PASSTHROUGH = "$is_args$args"

# Sources that must redirect but have no file on disk to derive them from:
# `/home-repair.html` was deleted in the 2026-07-17 two-path restructure and
# its extensionless twin never existed as a file, yet both still receive
# legacy inbound links. Everything else in the map comes from the repo.
LEGACY_REDIRECT_SOURCES: dict[str, str] = {
    "/home-repair.html": "/residential-construction",
    "/home-repair": "/residential-construction",
}


def _path_only(target: str) -> str:
    """Strip query + fragment: `/x?a=1#b` -> `/x`.

    nginx keeps `#home-repair` on the home-repair hop (fragment support is
    undocumented for CF-style `_redirects`, so Cloudflare omits it). The two
    stacks agree on the *destination page*, which is what the redirect map
    compares.
    """
    return re.split(r"[?#]", target, maxsplit=1)[0]


def expected_redirect_map(repo_root: Path) -> dict[str, str]:
    """THE shared source of truth: `{source -> clean destination}`.

    Every serving stack (Cloudflare `_redirects`, nginx `nginx.conf`) is
    checked against this one dict, so "both stacks agree" is asserted by
    construction rather than by two hand-maintained lists that can drift.
    Derived from what is actually on disk, so a new page added without its
    redirect rules fails on both stacks immediately.

    `404.html` is excluded: it is served internally (CF `not_found_handling`,
    nginx `error_page ... internal;`), never linked and never indexed.
    """
    mapping = dict(LEGACY_REDIRECT_SOURCES)
    for page in sorted(p.stem for p in repo_root.glob("*.html")):
        if page == "404":
            continue
        mapping[f"/{page}.html"] = "/" if page == "index" else f"/{page}"
    return mapping


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
            f"301s that form, so this URL redirects away from itself"
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
            f"worker 301s it, so every click pays an extra hop; link '/{page}'"
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


def _parse_redirect_rules(text: str) -> list[tuple[str, str, str]]:
    """(src, dst, code) for every parseable rule; comments/blank lines skipped."""
    rules: list[tuple[str, str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = REDIRECT_LINE_RE.match(line)
        if m:
            rules.append((m.group("src"), m.group("dst"), m.group("code")))
    return rules


def check_redirect_completeness(repo_root: Path, text: str) -> list[str]:
    """Contract 8 — every shipped page's `.html` form 301s, one hop, no chains.

    Driven by what is actually on disk rather than a hard-coded page list, so a
    new page added to the repo without its `_redirects` rule fails immediately
    instead of quietly inheriting CF's 307.
    """
    errors: list[str] = []
    rules = _parse_redirect_rules(text)

    # Cloudflare applies the FIRST matching rule, not the last. Building this
    # map last-wins would let a stray 302 prepended above the real 301 pass the
    # suite and then deploy as a 302 (Codex review, 2026-08-12). Keep the first
    # occurrence and reject duplicate sources outright — a duplicated source is
    # always either dead weight or a silent override.
    by_src: dict[str, tuple[str, str]] = {}
    for src, dst, code in rules:
        if src in by_src:
            errors.append(
                f"_redirects: duplicate rule for {src!r} — Cloudflare applies "
                f"the FIRST match ({by_src[src][0]!r} {by_src[src][1]}), so the "
                f"later rule ({dst!r} {code}) is silently dead; delete one"
            )
            continue
        by_src[src] = (dst, code)

    # Driven by the shared redirect map, so Cloudflare and nginx are measured
    # against the same yardstick (contract 6b compares the two stacks directly).
    for src, want_dst in sorted(expected_redirect_map(repo_root).items()):
        found = by_src.get(src)
        if found is None:
            errors.append(
                f"_redirects: no rule for {src!r} — without an explicit rule "
                f"Cloudflare's html_handling answers 307 Temporary, so Google "
                f"keeps {src!r} as a live index candidate instead of "
                f"consolidating it into {want_dst!r}; add "
                f"`{src} {want_dst} 301`"
            )
            continue
        dst, code = found
        if dst != want_dst:
            errors.append(
                f"_redirects: rule {src!r} targets {dst!r}, expected "
                f"{want_dst!r} (the clean path that serves 200 directly)"
            )
        if code != "301":
            errors.append(
                f"_redirects: rule {src!r} uses status {code} — a permanent "
                f"URL migration must be 301, or ranking signals are not "
                f"consolidated onto {want_dst!r}"
            )

    # Chain + loop guards. A target that is also a source means the browser
    # (and the crawler) pays two hops; a rule pointing at itself never settles.
    # Targets are normalized (query + fragment stripped) before comparison —
    # `/a -> /b#section` still lands on `/b`, so if `/b` is a redirect source
    # that is a chain even though the raw strings differ.
    sources = {src for src, _, _ in rules}
    for src, dst, _code in rules:
        dst_path = re.split(r"[?#]", dst, maxsplit=1)[0]
        if dst_path == src:
            errors.append(f"_redirects: rule {src!r} points at itself — redirect LOOP")
        elif dst_path in sources:
            errors.append(
                f"_redirects: rule {src!r} targets {dst!r}, which is itself a "
                f"redirect source — that is a redirect CHAIN (two hops); point "
                f"{src!r} at the final destination instead"
            )
    return errors


# Cloudflare `html_handling` values under which the clean paths this whole arc
# depends on still serve 200 directly:
#   auto-trailing-slash (the default) / drop-trailing-slash -> `/page` serves.
#   force-trailing-slash -> `/page` REDIRECTS to `/page/`, which would turn
#     every `.html` 301 into a two-hop chain AND make every submitted sitemap
#     URL a redirect during Search Console's first crawl.
#   none -> `/page` stops resolving entirely; every canonical, sitemap loc and
#     internal link 404s.
SAFE_HTML_HANDLING = ("auto-trailing-slash", "drop-trailing-slash")
HTML_HANDLING_RE = re.compile(r'"html_handling"\s*:\s*"(?P<value>[^"]*)"')


def check_wrangler_html_handling(text: str) -> list[str]:
    """Contract 9 — the worker config keeps clean paths serving 200 directly.

    The `_redirects` rules are only one hop because their targets resolve
    without a further redirect. That is a property of `html_handling`, which
    lives in a different file — so locking the rules without locking this
    leaves the arc breakable from outside the test's line of sight
    (Codex review, 2026-08-12).
    """
    m = HTML_HANDLING_RE.search(text)
    if m is None:
        # Absent = Cloudflare's default, `auto-trailing-slash`. Safe.
        return []
    value = m.group("value")
    if value not in SAFE_HTML_HANDLING:
        return [
            f"wrangler.jsonc: html_handling={value!r} — the clean paths that "
            f"every canonical, sitemap <loc> and `_redirects` target points at "
            f"would no longer serve 200 directly. Use one of "
            f"{list(SAFE_HTML_HANDLING)} (or omit it for the default)"
        ]
    return []


def _strip_nginx_comments(text: str) -> str:
    """Drop `# ...` comments so prose about redirects can't satisfy a check.

    nginx starts a comment only where `#` begins a token — a `#` inside a
    value does not. `return 301 /residential-construction#home-repair;` is a
    real, working directive (the fragment ships in the Location header), so a
    naive `#.*` strip would delete its terminating `;` and make the directive
    invisible to every check below.
    """
    return re.sub(r"(?m)(^|\s)#[^\n]*", r"\1", text)


def _nginx_location_bodies(text: str) -> dict[str, str]:
    """`{matcher: block body}` for every `location <matcher> { ... }`.

    Brace-matched rather than regex-terminated, so a nested block (nginx
    allows `if`/`location` nesting) cannot end the parent block early. Same
    approach as tests/test_nginx_headers.py.
    """
    out: dict[str, str] = {}
    for m in re.finditer(r"location\s+([^{]+?)\s*\{", text):
        matcher = re.sub(r"\s+", " ", m.group(1).strip())
        depth = 1
        i = m.end()
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    out[matcher] = text[m.end():i]
                    break
            i += 1
    return out


def nginx_redirect_map(text: str) -> tuple[dict[str, str], list[str]]:
    """`({source -> destination path}, structural errors)` for nginx.conf.

    Only EXACT-match blocks (`location = /x`) count as a redirect source.
    That is deliberate, and it is where nginx's precedence rules differ from
    Cloudflare's: Cloudflare applies the FIRST matching line in `_redirects`
    (so order is the tie-breaker), whereas nginx resolves by *specificity* —
    an exact `=` match short-circuits the whole location search before any
    prefix or regex location is considered, regardless of file order. A
    prefix or regex `location /x.html` would still beat `location /` (longer
    prefix / regex-over-prefix), but its precedence then depends on the rest
    of the file; the `=` form does not. Requiring `=` makes the redirect
    unconditionally win, so a future edit that reorders the file cannot
    resurrect the 200.
    """
    errors: list[str] = []
    mapping: dict[str, str] = {}
    for matcher, body in _nginx_location_bodies(_strip_nginx_comments(text)).items():
        rm = NGINX_RETURN_RE.search(body)
        if rm is None:
            continue
        target = rm.group("target")
        if QUERY_PASSTHROUGH not in target:
            errors.append(
                f"nginx.conf: `location {matcher}` returns {target!r} without "
                f"`{QUERY_PASSTHROUGH}` — nginx sends exactly the URL written "
                f"and DROPS the query string, so `?intent=` / `?utm_*` die on "
                f"the hop and the intake form lands unprefilled with no "
                f"attribution. Cloudflare preserves the query; the fallback "
                f"must too (money path)"
            )
        target = target.replace(QUERY_PASSTHROUGH, "")
        if not matcher.startswith("= "):
            errors.append(
                f"nginx.conf: `location {matcher}` issues `return 301 {target}` "
                f"but is not an exact (`location = ...`) match — its precedence "
                f"then depends on file order/regex rules instead of winning "
                f"outright over `location /`"
            )
            continue
        src = matcher[2:].strip()
        if src in mapping:
            errors.append(f"nginx.conf: duplicate `location = {src}` redirect block")
        mapping[src] = _path_only(target)
    return mapping, errors


def check_nginx(repo_root: Path, text: str) -> list[str]:
    """Contract 6a — the fallback can actually serve the clean paths."""
    errors: list[str] = []
    bodies = _nginx_location_bodies(_strip_nginx_comments(text))
    root_loc = bodies.get("/")
    if root_loc is None:
        errors.append("nginx.conf: no `location / { ... }` block found")
    else:
        tf = re.search(r"try_files\s+(?P<body>[^;]+);", root_loc)
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
    for m in NGINX_RETURN_RE.finditer(_strip_nginx_comments(text)):
        target = m.group("target")
        if re.search(r"\.html(?:[?#]|$)", target):
            errors.append(
                f"nginx.conf: `return 301 {target}` uses the `.html` form — the "
                f"fallback should mirror the clean CF target"
            )

    # The homepage loop guard. `index index.html;` makes a request for `/`
    # internally redirect to `/index.html`, and that internal redirect re-runs
    # location matching — so a bare `return 301 /` inside
    # `location = /index.html` bounces `/` -> `/index.html` -> `/` forever.
    # An explicit `location = /` that serves the file itself (try_files, which
    # does NOT re-run location matching when the file exists) breaks the cycle.
    ng_map, _ = nginx_redirect_map(text)
    if "/index.html" in ng_map and "= /" not in bodies:
        errors.append(
            "nginx.conf: `location = /index.html` redirects but there is no "
            "`location = / { try_files /index.html =404; }` — the `index` "
            "directive would internally redirect `/` to `/index.html`, hit the "
            "301 and send the homepage into a redirect LOOP"
        )
    return errors


def check_stack_parity(repo_root: Path, redirects_text: str, nginx_text: str) -> list[str]:
    """Contract 6b — Cloudflare and nginx implement the SAME redirect map.

    Both stacks are compared against `expected_redirect_map()` *and* against
    each other, so the failure mode this was written for — one stack 301ing
    while the other serves 200, restoring duplicate content on failover — is
    impossible to reintroduce on either side.
    """
    expected = expected_redirect_map(repo_root)
    cf_map = {
        src: _path_only(dst)
        for src, dst, code in _parse_redirect_rules(redirects_text)
        if code.startswith("30")
    }
    ng_map, errors = nginx_redirect_map(nginx_text)

    for src in sorted(set(expected) | set(cf_map) | set(ng_map)):
        want = expected.get(src)
        cf = cf_map.get(src)
        ng = ng_map.get(src)
        if want is not None and ng is None:
            errors.append(
                f"nginx.conf: no `location = {src}` redirect — Cloudflare 301s "
                f"{src!r} to {want!r} while the Railway fallback serves it 200 "
                f"(try_files' `$uri` arm finds the file), so a failover restores "
                f"the duplicate-content shape; add "
                f"`location = {src} {{ return 301 {want}; }}`"
            )
        elif want is not None and ng != want:
            errors.append(
                f"nginx.conf: `location = {src}` redirects to {ng!r}, expected "
                f"{want!r} — the two stacks must land on the same page"
            )
        if want is None and ng is not None and cf is None:
            errors.append(
                f"nginx.conf redirects {src!r} -> {ng!r} but `_redirects` has no "
                f"rule for it — the fallback would send visitors somewhere the "
                f"live host does not"
            )
        if want is None and cf is not None and ng is None:
            errors.append(
                f"_redirects redirects {src!r} -> {cf!r} but nginx.conf has no "
                f"`location = {src}` — the fallback would serve it instead"
            )
        if cf is not None and ng is not None and cf != ng:
            errors.append(
                f"redirect DRIFT for {src!r}: Cloudflare -> {cf!r}, nginx -> "
                f"{ng!r}; the two serving stacks disagree"
            )
    return errors


def check_no_www(repo_root: Path) -> list[str]:
    """Contract 7 — apex is the sole canonical host; `www` must appear in no shipped file."""
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
        redirects_text = redirects.read_text(encoding="utf-8")
        errors.extend(check_redirects(redirects_text))
        errors.extend(check_redirect_completeness(repo_root, redirects_text))

    wrangler = repo_root / "wrangler.jsonc"
    if wrangler.is_file():
        errors.extend(check_wrangler_html_handling(wrangler.read_text(encoding="utf-8")))

    nginx = repo_root / "nginx.conf"
    if not nginx.is_file():
        errors.append("nginx.conf missing")
    else:
        nginx_text = nginx.read_text(encoding="utf-8")
        errors.extend(check_nginx(repo_root, nginx_text))
        if redirects.is_file():
            errors.extend(check_stack_parity(repo_root, redirects_text, nginx_text))

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
/commercial-industrial.html /commercial-industrial 301
"""

BASELINE_NGINX = """server {
    listen 8080;
    location / {
        try_files $uri $uri.html $uri/ =404;
    }
    location = /home-repair.html {
        return 301 /residential-construction$is_args$args#home-repair;
    }
    location = /home-repair {
        return 301 /residential-construction$is_args$args#home-repair;
    }
    location = /commercial-industrial.html {
        return 301 /commercial-industrial$is_args$args;
    }
}
"""


BASELINE_WRANGLER = """{
  "name": "big7",
  "compatibility_date": "2026-07-01",
  "assets": { "directory": "./", "not_found_handling": "404-page" }
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
    (root / "wrangler.jsonc").write_text(BASELINE_WRANGLER, encoding="utf-8")


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
        attempted: list[str] = []

        def add(label: str, filename: str, content: str, expect: str) -> None:
            attempted.append(label)
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
                "return 301 /residential-construction$is_args$args#home-repair;",
                "return 301 /residential-construction.html#home-repair;",
            ),
            "should mirror the clean CF target",
        )

        # --- contract 8: `.html` -> clean must be an explicit, one-hop 301 ---
        add(
            "`.html` rule deleted (silently falls back to CF's 307)",
            "_redirects",
            BASELINE_REDIRECTS.replace(
                "/commercial-industrial.html /commercial-industrial 301\n", ""
            ),
            "no rule for '/commercial-industrial.html'",
        )
        add(
            "`.html` rule downgraded 301 -> 302 (temporary signal)",
            "_redirects",
            BASELINE_REDIRECTS.replace(
                "/commercial-industrial.html /commercial-industrial 301",
                "/commercial-industrial.html /commercial-industrial 302",
            ),
            "must be 301",
        )
        add(
            "`.html` rule retargeted away from its clean path",
            "_redirects",
            BASELINE_REDIRECTS.replace(
                "/commercial-industrial.html /commercial-industrial 301",
                "/commercial-industrial.html / 301",
            ),
            "expected '/commercial-industrial'",
        )
        add(
            "redirect CHAIN (target is another rule's source)",
            "_redirects",
            BASELINE_REDIRECTS.replace(
                "/home-repair.html /residential-construction 301",
                "/home-repair.html /home-repair 301",
            ),
            "redirect CHAIN",
        )
        add(
            "redirect LOOP (rule points at itself)",
            "_redirects",
            BASELINE_REDIRECTS.replace(
                "/commercial-industrial.html /commercial-industrial 301",
                "/commercial-industrial.html /commercial-industrial.html 301",
            ),
            "redirect LOOP",
        )

        # --- gaps surfaced by the Codex second opinion, 2026-08-12 ---
        add(
            "duplicate source prepended (CF applies the FIRST match)",
            "_redirects",
            "/commercial-industrial.html /commercial-industrial 302\n" + BASELINE_REDIRECTS,
            "duplicate rule for '/commercial-industrial.html'",
        )
        add(
            "CHAIN hidden behind a fragment on the target",
            "_redirects",
            BASELINE_REDIRECTS.replace(
                "/home-repair.html /residential-construction 301",
                "/home-repair.html /home-repair#section 301",
            ),
            "redirect CHAIN",
        )
        add(
            "html_handling forces trailing slash (every clean URL redirects)",
            "wrangler.jsonc",
            BASELINE_WRANGLER.replace(
                '"not_found_handling": "404-page"',
                '"not_found_handling": "404-page", "html_handling": "force-trailing-slash"',
            ),
            "would no longer serve 200 directly",
        )
        add(
            "html_handling disabled (every clean URL 404s)",
            "wrangler.jsonc",
            BASELINE_WRANGLER.replace(
                '"not_found_handling": "404-page"',
                '"not_found_handling": "404-page", "html_handling": "none"',
            ),
            "would no longer serve 200 directly",
        )

        # --- contract 6b: the two serving stacks must agree (2026-08-12) ---
        add(
            "nginx drops a `.html` redirect (fallback serves 200 -> duplicate content)",
            "nginx.conf",
            BASELINE_NGINX.replace(
                "    location = /commercial-industrial.html {\n"
                "        return 301 /commercial-industrial$is_args$args;\n"
                "    }\n",
                "",
            ),
            "no `location = /commercial-industrial.html` redirect",
        )
        add(
            "nginx redirect demoted to a prefix match (precedence now order-dependent)",
            "nginx.conf",
            BASELINE_NGINX.replace(
                "location = /commercial-industrial.html {",
                "location /commercial-industrial.html {",
            ),
            "not an exact",
        )
        add(
            "nginx redirect points at a different page than Cloudflare",
            "nginx.conf",
            BASELINE_NGINX.replace(
                "        return 301 /commercial-industrial$is_args$args;",
                "        return 301 /residential-construction$is_args$args;",
            ),
            "redirect DRIFT",
        )
        add(
            "nginx 301s /index.html with no `location = /` (homepage redirect loop)",
            "nginx.conf",
            BASELINE_NGINX.replace(
                "    location = /home-repair.html {",
                "    location = /index.html {\n        return 301 /$is_args$args;\n    }\n"
                "    location = /home-repair.html {",
            ),
            "redirect LOOP",
        )
        add(
            "nginx redirects a source Cloudflare knows nothing about",
            "nginx.conf",
            BASELINE_NGINX.replace(
                "    location = /home-repair.html {",
                "    location = /old-lander {\n        return 301 /$is_args$args;\n    }\n"
                "    location = /home-repair.html {",
            ),
            "`_redirects` has no rule for it",
        )
        add(
            "nginx redirect drops the query string (money-path prefill dies)",
            "nginx.conf",
            BASELINE_NGINX.replace(
                "        return 301 /commercial-industrial$is_args$args;",
                "        return 301 /commercial-industrial;",
            ),
            "DROPS the query string",
        )

        total = len(attempted)
        if not_caught:
            print(f"SELFTEST: {len(not_caught)} mutation(s) not caught: {not_caught}")
            return 1
        print(f"SELFTEST: all {total} mutations caught")
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
