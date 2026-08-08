"""
nginx.conf security-header + cache-control contract test.

Why: Rung 1 HARDEN claims 5 defense-in-depth headers (HSTS, XCTO, XFO,
Referrer-Policy, Permissions-Policy) plus per-location Cache-Control on
every response. But nginx's `add_header` directive is NOT inherited into
any `location` block that declares even one add_header of its own —
declaring `add_header Cache-Control` inside `location = /index.html`
silently drops the 5 server-level security add_headers from that response
unless they are repeated inline. This is a real footgun the file's inline
comment (nginx.conf L18-24 and L52-55) already warns about; the test
turns that warning into an assertion so a careless future edit inside
any protected location can't silently ship an unprotected surface.

The six existing suites (JSON-LD, seo-files, conversion, og/twitter,
assets, anchors) all assert on files served BY nginx — none of them
assert on the server config itself. Since we ship as a static site
behind nginx, the config IS money code: a missing HSTS header lets a
MITM downgrade the first visit to HTTP, and a Cache-Control drift on
`/index.html` back to `immutable, max-age=31536000` (the site-wide
default) means CDNs pin a stale HTML for a year even after redeploy.

Contract asserted:
  1. Server block has all 5 security headers + Vary: Accept-Encoding +
     the long-cache default.
  2. Each protected location (`/index.html`, `/robots.txt`,
     `/sitemap.xml`, `/404.html`) declares at least one add_header
     itself — which triggers nginx inheritance reset — and therefore
     MUST repeat all 5 security headers inline.
  3. `/index.html` Cache-Control is short-cache (`max-age=0,
     must-revalidate`) — never immutable.
  4. `/robots.txt` + `/sitemap.xml` + `/404.html` Cache-Control is
     1-hour (`max-age=3600`) — never the site-wide 1-year immutable
     default (crawlers and CDNs must re-fetch these on their own
     schedule).
  5. `/404.html` block declares `internal;` (public GETs to it must
     404, only reachable via error_page).
  6. `location /` `try_files` fallback ends in `=404`, NOT `/index.html`
     — the historical regression this codebase already suffered once
     (see nginx.conf L36-40 comment). Rewriting typos to `/` with 200
     hurts SEO.
  7. HSTS `max-age` is at least 6 months (15768000 seconds — the
     preload-eligibility floor).

Python 3.11+ stdlib only (`re`, `pathlib`, `sys`). No pip, no network,
no nginx binary required.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NGINX_CONF = REPO_ROOT / "nginx.conf"

# HSTS preload-eligibility floor (Chromium HSTS preload spec) — 6 months.
# The current file ships 31536000 (1 year); we assert only the floor so
# a future move to a longer max-age doesn't break the test.
HSTS_MIN_MAXAGE = 15_768_000

# The 5 defense-in-depth headers Rung 1 HARDEN promised. Values below are
# the exact strings today; the contract is EQUALITY (not substring) — any
# drift (e.g., XFO=SAMEORIGIN instead of DENY, Referrer-Policy relaxed to
# unsafe-url) fires the test.
REQUIRED_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
    # Strict-Transport-Security is checked separately below because
    # max-age is a numeric floor, not an equality check.
}

# Protected locations — every response served from these must carry the
# 5 security headers. Each entry: (nginx location matcher, expected
# Cache-Control value).
PROTECTED_LOCATIONS: dict[str, str] = {
    "= /index.html": "public, max-age=0, must-revalidate",
    "= /robots.txt": "public, max-age=3600",
    "= /sitemap.xml": "public, max-age=3600",
    "= /404.html": "public, max-age=3600",
}


def _strip_comments(conf: str) -> str:
    """Strip nginx `# ...` comments so they can't fool the location-block
    regex. A comment that reads `# nested location = /foo below` would
    otherwise satisfy `location\\s+[^{]+?\\s*\\{` all the way through to
    the next real block's opening brace."""
    return re.sub(r"#[^\n]*", "", conf)


def _extract_server_body(conf: str) -> str:
    """Return the body inside the outermost `server { ... }` block."""
    m = re.search(r"\bserver\s*\{", conf)
    if not m:
        raise ValueError("no `server {` block in nginx.conf")
    start = m.end()
    depth = 1
    i = start
    while i < len(conf):
        c = conf[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return conf[start:i]
        i += 1
    raise ValueError("unbalanced braces in `server { ... }` block")


def _extract_location_bodies(server_body: str) -> dict[str, str]:
    """Return {location_matcher: block_body} for every `location <M> { ... }`
    block found in `server_body`. The matcher is whitespace-normalized
    (e.g., 'location  =  /index.html {' → '= /index.html')."""
    out: dict[str, str] = {}
    for m in re.finditer(r"location\s+([^{]+?)\s*\{", server_body):
        matcher = re.sub(r"\s+", " ", m.group(1).strip())
        depth = 1
        i = m.end()
        while i < len(server_body):
            c = server_body[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    out[matcher] = server_body[m.end():i]
                    break
            i += 1
        else:
            raise ValueError(f"unbalanced braces in location {matcher} block")
    return out


def _server_direct_directives(server_body: str, location_bodies: dict[str, str]) -> str:
    """Return `server_body` with every location block body removed, so
    directives declared directly at server scope are the only thing left.
    Prevents an add_header inside `location /index.html` from satisfying
    a server-scope assertion."""
    scrubbed = server_body
    for body in location_bodies.values():
        scrubbed = scrubbed.replace(body, "")
    return scrubbed


def _find_add_header(block: str, name: str) -> str | None:
    """Return the value of the last matching `add_header <name> "..."` in
    `block`, or None. Last-match matters because nginx applies the last
    directive at each config level; using the last also mirrors what
    ships at runtime."""
    matches = re.findall(
        rf'add_header\s+{re.escape(name)}\s+"([^"]*)"', block
    )
    return matches[-1] if matches else None


def _check_security_headers(block_name: str, body: str) -> list[str]:
    errors: list[str] = []
    hsts_raw = _find_add_header(body, "Strict-Transport-Security")
    if hsts_raw is None:
        errors.append(f"{block_name}: missing add_header Strict-Transport-Security")
    else:
        m = re.search(r"max-age=(\d+)", hsts_raw)
        if not m:
            errors.append(
                f"{block_name}: HSTS has no max-age directive: {hsts_raw!r}"
            )
        elif int(m.group(1)) < HSTS_MIN_MAXAGE:
            errors.append(
                f"{block_name}: HSTS max-age={m.group(1)} below floor {HSTS_MIN_MAXAGE} "
                f"(< 6 months — HSTS preload rejects this)"
            )
        if "includeSubDomains" not in hsts_raw:
            errors.append(
                f"{block_name}: HSTS missing includeSubDomains: {hsts_raw!r}"
            )
    for header, expected in REQUIRED_SECURITY_HEADERS.items():
        val = _find_add_header(body, header)
        if val is None:
            errors.append(f"{block_name}: missing add_header {header}")
        elif val != expected:
            errors.append(
                f"{block_name}: add_header {header} = {val!r}, expected {expected!r}"
            )
    return errors


def check_nginx_conf(conf: str) -> list[str]:
    """Return a list of error strings. Empty list = PASS."""
    errors: list[str] = []

    try:
        server_body = _extract_server_body(conf)
    except ValueError as e:
        return [f"parse error: {e}"]

    try:
        location_bodies = _extract_location_bodies(server_body)
    except ValueError as e:
        return [f"parse error: {e}"]

    server_direct = _server_direct_directives(server_body, location_bodies)
    errors.extend(_check_security_headers("server", server_direct))

    if _find_add_header(server_direct, "Vary") is None:
        errors.append("server: missing add_header Vary (required for gzip CDN correctness)")

    server_cache = _find_add_header(server_direct, "Cache-Control")
    if server_cache is None:
        errors.append("server: missing default add_header Cache-Control")
    elif "immutable" not in server_cache:
        errors.append(
            f"server: default Cache-Control = {server_cache!r} — static asset default "
            f"should be long-cache immutable"
        )

    for matcher, expected_cc in PROTECTED_LOCATIONS.items():
        if matcher not in location_bodies:
            errors.append(f"missing `location {matcher}` block")
            continue
        body = location_bodies[matcher]
        errors.extend(_check_security_headers(f"location {matcher}", body))
        cc = _find_add_header(body, "Cache-Control")
        if cc is None:
            errors.append(f"location {matcher}: missing add_header Cache-Control")
        elif cc != expected_cc:
            errors.append(
                f"location {matcher}: Cache-Control = {cc!r}, expected {expected_cc!r}"
            )

    if "= /404.html" in location_bodies:
        if not re.search(r"\binternal\s*;", location_bodies["= /404.html"]):
            errors.append(
                "location = /404.html: missing `internal;` directive "
                "(public GETs to /404.html should 404, not serve the page)"
            )

    root_loc = location_bodies.get("/")
    if root_loc is None:
        errors.append("missing `location /` block")
    else:
        tf = re.search(r"try_files\s+([^;]+);", root_loc)
        if tf is None:
            errors.append("location /: missing try_files directive")
        else:
            tf_body = tf.group(1).strip()
            if not re.search(r"=\s*404\s*$", tf_body):
                errors.append(
                    f"location /: try_files fallback is {tf_body!r} — must end in "
                    f"`=404`, not `/index.html` (rewriting typos to / hurts SEO)"
                )

    return errors


# ---------------------------------------------------------------------------
# Selftest — mutate a synthetic-but-realistic nginx.conf and require each
# break to raise a specific error substring. Matches the tick-6/7/10/11/12
# /13/14 pattern.
# ---------------------------------------------------------------------------

def _baseline_conf() -> str:
    security = "\n".join(
        f'    add_header {h} "{v}" always;' for h, v in [
            ("Strict-Transport-Security", "max-age=31536000; includeSubDomains"),
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("Referrer-Policy", "strict-origin-when-cross-origin"),
            ("Permissions-Policy", "geolocation=(), microphone=(), camera=(), payment=()"),
        ]
    )
    loc_security = security.replace("    ", "        ")
    return f"""server {{
    listen 8080;
    root /usr/share/nginx/html;
    index index.html;

    add_header Vary "Accept-Encoding" always;
{security}
    add_header Cache-Control "public, max-age=31536000, immutable" always;

    location = /index.html {{
{loc_security}
        add_header Cache-Control "public, max-age=0, must-revalidate" always;
    }}
    location = /robots.txt {{
{loc_security}
        add_header Cache-Control "public, max-age=3600" always;
    }}
    location = /sitemap.xml {{
{loc_security}
        add_header Cache-Control "public, max-age=3600" always;
    }}
    location = /404.html {{
        internal;
{loc_security}
        add_header Cache-Control "public, max-age=3600" always;
    }}
    location / {{
        try_files $uri $uri/ =404;
    }}
    error_page 404 /404.html;
}}
"""


def _expect_pass(label: str, conf: str) -> str | None:
    errs = check_nginx_conf(conf)
    if errs:
        return f"{label}: expected PASS, got errors: {errs}"
    return None


def _expect_fail(label: str, conf: str, needle: str) -> str | None:
    errs = check_nginx_conf(conf)
    if not errs:
        return f"{label}: expected failure containing {needle!r}, got PASS"
    if not any(needle in e for e in errs):
        return f"{label}: expected failure containing {needle!r}, got errors: {errs}"
    return None


def selftest() -> int:
    baseline = _baseline_conf()
    misses: list[str] = []

    comment_probe = baseline.replace(
        "server {",
        "server {\n    # nested location = /decoy { would fool a naive parser",
        1,
    )
    err = _expect_pass("comment-with-fake-location", _strip_comments(comment_probe))
    if err:
        misses.append(err)

    err = _expect_pass("baseline", baseline)
    if err:
        misses.append(err)

    def drop_first(needle: str, conf: str) -> str:
        return conf.replace(needle, "", 1)

    mutations: list[tuple[str, str, str]] = [
        (
            "HSTS dropped from server scope",
            re.sub(
                r'    add_header Strict-Transport-Security[^\n]*\n',
                "",
                baseline,
                count=1,
            ),
            "server: missing add_header Strict-Transport-Security",
        ),
        (
            "HSTS dropped from /index.html (silent inheritance reset)",
            baseline.replace(
                '        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;\n',
                "",
                1,
            ),
            "location = /index.html: missing add_header Strict-Transport-Security",
        ),
        (
            "X-Frame-Options relaxed to SAMEORIGIN",
            baseline.replace('"DENY"', '"SAMEORIGIN"'),
            "X-Frame-Options",
        ),
        (
            "Referrer-Policy relaxed to unsafe-url",
            baseline.replace(
                '"strict-origin-when-cross-origin"', '"unsafe-url"'
            ),
            "Referrer-Policy",
        ),
        (
            "/index.html cache reverted to server-wide immutable",
            baseline.replace(
                '"public, max-age=0, must-revalidate"',
                '"public, max-age=31536000, immutable"',
            ),
            "location = /index.html: Cache-Control",
        ),
        (
            "try_files fallback reverted to /index.html (SEO regression)",
            baseline.replace(
                "try_files $uri $uri/ =404;",
                "try_files $uri $uri/ /index.html;",
            ),
            "try_files fallback",
        ),
        (
            "HSTS max-age below 6-month floor",
            baseline.replace("max-age=31536000", "max-age=3600"),
            "below floor",
        ),
        (
            "Vary missing at server scope",
            baseline.replace(
                '    add_header Vary "Accept-Encoding" always;\n', ""
            ),
            "missing add_header Vary",
        ),
        (
            "Permissions-Policy dropped from /robots.txt",
            re.sub(
                r'(location = /robots\.txt \{[^}]*?)        add_header Permissions-Policy[^\n]*\n',
                r"\1",
                baseline,
                count=1,
                flags=re.DOTALL,
            ),
            "location = /robots.txt: missing add_header Permissions-Policy",
        ),
        (
            "/robots.txt block missing entirely",
            re.sub(
                r'    location = /robots\.txt \{[^}]*\}\n',
                "",
                baseline,
                count=1,
                flags=re.DOTALL,
            ),
            "missing `location = /robots.txt` block",
        ),
        (
            "/404.html missing internal; (public GETs would serve it)",
            baseline.replace("        internal;\n", ""),
            "missing `internal;`",
        ),
        (
            "HSTS missing includeSubDomains",
            baseline.replace(
                "max-age=31536000; includeSubDomains", "max-age=31536000"
            ),
            "includeSubDomains",
        ),
    ]

    for label, mutated, needle in mutations:
        err = _expect_fail(label, mutated, needle)
        if err:
            misses.append(err)

    if misses:
        for m in misses:
            print(f"SELFTEST FAIL: {m}", file=sys.stderr)
        return 1

    print(f"SELFTEST OK: baseline PASS + {len(mutations)}/{len(mutations)} mutations caught")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    if not NGINX_CONF.exists():
        print(f"FAIL: {NGINX_CONF} not found", file=sys.stderr)
        return 1

    conf = _strip_comments(NGINX_CONF.read_text(encoding="utf-8"))
    errors = check_nginx_conf(conf)
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(
        f"OK: nginx.conf server block + {len(PROTECTED_LOCATIONS)} protected locations "
        f"all carry the 5 security headers; per-location Cache-Control matches spec; "
        f"try_files falls through to =404; HSTS max-age >= {HSTS_MIN_MAXAGE}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
