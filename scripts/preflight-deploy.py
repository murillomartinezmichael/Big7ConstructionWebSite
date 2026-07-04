#!/usr/bin/env python3
"""preflight-deploy.py — pre-deploy readiness check for Big7Construction.

Runs in ~1 second. Verifies the static site will boot on Railway
(nginx:alpine as USER nginx on ${PORT:-8080}), that index.html is real
content, that the images/ folder is intact (all referenced images resolve),
and that the security headers survived any nginx.conf edits.

Modes
-----
    python scripts/preflight-deploy.py             # base checks
    python scripts/preflight-deploy.py --live URL  # + curl the live URL
    python scripts/preflight-deploy.py --strict    # fail on warn-level issues

What it checks
--------------
    1. Dockerfile: FROM nginx:alpine + USER nginx + PORT substitution
       + COPY index.html + COPY images/
    2. nginx.conf: NGINX_PORT placeholder + 5 security headers present
       + same 5 re-declared inside `location = /index.html` (nginx
       add_header inheritance resets on nested blocks)
    3. index.html: exists + > 20 KB + all locally-referenced images resolve
    4. Branding: Big 7 Construction site signatures present
       (no accidental placeholder/lorem content shipped)
    5. --live: probe the given URL + verify signature strings in the body
       so we don't mistake a squatted URL for our own site

Exit codes: 0 all green, 1 any base check failed. Suitable as a CI gate.
"""

from __future__ import annotations
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    pass

REPO = Path(__file__).resolve().parent.parent

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

failures = 0
warnings_count = 0
skips = 0

# Signature strings we expect in our own served body. If --live probes a URL
# and none appear, we've got the wrong URL (squatted or fallback).
SITE_SIGNATURES = [
    "Big 7 Construction",
    "info@big7construction.com",
]

REQUIRED_HEADERS = [
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
]

# Placeholder markers that signal an unshipped-content leak. We deliberately
# exclude a bare "\bplaceholder\b" pattern because HTML input/textarea forms
# use `placeholder="..."` as a legitimate attribute for the hint text.
LOREM_PATTERNS = [
    r"\blorem ipsum\b",
    r"\bTODO:",
    r"\bXXX:",
    r"\bFIXME:",
]


def ok(label: str, detail: str = "") -> None:
    d = f"{DIM}  {detail}{RESET}" if detail else ""
    print(f"  {GREEN}✓{RESET} {label}{d}")


def fail(label: str, detail: str = "") -> None:
    global failures
    d = f"  {detail}" if detail else ""
    print(f"  {RED}✗{RESET} {label}{d}")
    failures += 1


def warn(label: str, detail: str = "") -> None:
    global warnings_count
    d = f"  {detail}" if detail else ""
    print(f"  {YELLOW}⚠{RESET} {label}{d}")
    warnings_count += 1


def skip(label: str, detail: str = "") -> None:
    global skips
    d = f"{DIM}  {detail}{RESET}" if detail else ""
    print(f"  {YELLOW}○{RESET} {label}{d}")
    skips += 1


def check_dockerfile() -> None:
    path = REPO / "Dockerfile"
    if not path.exists():
        fail("Dockerfile missing")
        return
    src = path.read_text(encoding="utf-8")
    checks = {
        "FROM nginx:alpine": "FROM nginx:alpine" in src or "from nginx:alpine" in src.lower(),
        "USER nginx (non-root)": re.search(r"^USER\s+nginx\b", src, re.MULTILINE) is not None,
        "PORT substitution": "${PORT" in src or "$PORT" in src,
        "COPY index.html": "index.html" in src and "COPY" in src.upper(),
        "COPY images/": "images/" in src and "COPY" in src.upper(),
        "COPY nginx.conf": "nginx.conf" in src and "COPY" in src.upper(),
    }
    missing = [k for k, v in checks.items() if not v]
    if missing:
        fail("Dockerfile incomplete", "missing: " + "; ".join(missing))
    else:
        ok("Dockerfile: nginx:alpine + USER nginx + PORT + all COPYs")


def check_nginx_conf() -> None:
    path = REPO / "nginx.conf"
    if not path.exists():
        fail("nginx.conf missing")
        return
    src = path.read_text(encoding="utf-8")

    if "NGINX_PORT" not in src:
        fail("nginx.conf missing NGINX_PORT placeholder", "Dockerfile sed replaces it at boot")
    else:
        ok("nginx.conf declares NGINX_PORT placeholder")

    missing_headers = [h for h in REQUIRED_HEADERS if h not in src]
    if missing_headers:
        fail(
            f"nginx.conf missing {len(missing_headers)} security header(s)",
            ", ".join(missing_headers),
        )
    else:
        ok(f"nginx.conf declares all {len(REQUIRED_HEADERS)} security headers")

    m = re.search(
        r"location\s*=\s*/index\.html\s*\{(.*?)\}",
        src,
        re.DOTALL,
    )
    if m:
        loc_body = m.group(1)
        loc_missing = [h for h in REQUIRED_HEADERS if h not in loc_body]
        if loc_missing:
            fail(
                f"`location = /index.html` drops {len(loc_missing)} inherited header(s)",
                ", ".join(loc_missing) + " (see comment in nginx.conf)",
            )
        else:
            ok("`location = /index.html` re-declares all 5 security headers")


def check_index_html() -> None:
    path = REPO / "index.html"
    if not path.exists():
        fail("index.html missing")
        return
    size = path.stat().st_size
    src = path.read_text(encoding="utf-8", errors="replace")

    if size < 20_000:
        fail(f"index.html is only {size} bytes", "expected > 20 KB for this site")
    else:
        ok(f"index.html present + {size // 1024} KB ({src.count(chr(10)) + 1} lines)")

    # Branding: signature strings must appear (defends against a placeholder ship).
    missing_sigs = [s for s in SITE_SIGNATURES if s not in src]
    if missing_sigs:
        fail(
            f"index.html missing {len(missing_sigs)} required signature string(s)",
            ", ".join(missing_sigs) + " — is this the right file?",
        )
    else:
        ok(f"index.html contains all {len(SITE_SIGNATURES)} brand signatures")

    # Lorem / TODO / placeholder markers should never ship.
    hits = []
    for pat in LOREM_PATTERNS:
        m = re.search(pat, src, re.IGNORECASE)
        if m:
            hits.append(pat)
    if hits:
        fail(
            f"index.html contains {len(hits)} placeholder marker(s)",
            "; ".join(hits) + " — unshipped content?",
        )
    else:
        ok("index.html contains no lorem/TODO/placeholder markers")


def check_images_folder() -> None:
    """Verify every locally-referenced image in index.html resolves under images/."""
    imgs_dir = REPO / "images"
    if not imgs_dir.exists() or not imgs_dir.is_dir():
        fail("images/ folder missing", "Dockerfile COPYs it into /usr/share/nginx/html/images/")
        return

    index = REPO / "index.html"
    if not index.exists():
        skip("images-referenced-in-html audit", "no index.html to audit")
        return

    src = index.read_text(encoding="utf-8", errors="replace")
    # Match src="images/..." or url(images/...) — locally-referenced only.
    local_refs = set(re.findall(r'(?:src|href)=["\'](images/[^"\']+)["\']', src))
    local_refs |= set(re.findall(r'url\((images/[^\)]+)\)', src))

    missing = []
    for ref in sorted(local_refs):
        p = REPO / ref
        if not p.exists():
            missing.append(ref)

    if not local_refs:
        skip("images-referenced-in-html audit", "no images/ refs in index.html")
    elif missing:
        fail(
            f"{len(missing)} of {len(local_refs)} images/ ref(s) don't resolve",
            "; ".join(missing[:3]) + (" ..." if len(missing) > 3 else ""),
        )
    else:
        ok(f"all {len(local_refs)} local images/ refs resolve on disk")


def check_live(url: str) -> None:
    if not url.startswith("http"):
        url = "https://" + url

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "preflight-deploy"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            code = resp.status
            body = resp.read(200_000).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        fail(f"HTTP error probing {url}", f"{e.code} {e.reason}")
        return
    except Exception as e:  # noqa: BLE001
        fail(f"probe failed for {url}", f"{type(e).__name__}: {e}")
        return

    if code != 200:
        fail(f"live probe {url}", f"HTTP {code}")
        return

    missing = [s for s in SITE_SIGNATURES if s not in body]
    if missing:
        fail(
            f"live URL responds 200 but body missing {len(missing)} signature(s)",
            f"missing: {', '.join(missing)} — is this URL squatted / wrong tenant?",
        )
    else:
        ok(f"live URL {url} serves Big7Construction", "signatures matched")


def main() -> int:
    args = sys.argv[1:]
    strict = "--strict" in args

    live_url = None
    if "--live" in args:
        try:
            live_url = args[args.index("--live") + 1]
        except IndexError:
            fail("--live requires a URL argument", "e.g. --live big7construction.example.com")

    print(f"\n{BOLD}Big7Construction preflight — deploy readiness{RESET}\n")

    check_dockerfile()
    check_nginx_conf()
    check_index_html()
    check_images_folder()

    if live_url:
        check_live(live_url)
    else:
        skip("live probe", "pass --live URL to verify prod serves Big7 (not a squatted URL)")

    print()
    if failures == 0 and (not strict or warnings_count == 0):
        s = "s" if skips != 1 else ""
        w = f", {warnings_count} warn" if warnings_count else ""
        print(f"{GREEN}{BOLD}READY{RESET}  {DIM}({skips} optional check{s} skipped{w}){RESET}\n")
        return 0
    else:
        fail_word = "check" if failures == 1 else "checks"
        extra = ""
        if warnings_count and strict:
            extra = f", {warnings_count} warn (strict mode)"
        if skips:
            extra += f", {skips} skipped"
        print(f"{RED}{BOLD}NOT READY{RESET}  {failures} {fail_word} failed{extra}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
