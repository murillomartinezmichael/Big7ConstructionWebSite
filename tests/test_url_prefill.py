"""URL-param prefill contract (bio-link landing).

Money path: `?intent=service:*` / `?type=<projectType>` / `?src=<slug>` on the
landing URL prefills the intake radio + textarea. A silent break here means
every TikTok/IG/email bio click hits a blank form. Locks the IIFE shape,
SAFE_PARAM whitelist, and `landing_prefill` attribution event.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "index.html"

IIFE_MARKER = "URL-param prefill (bio-link landing)"

REQUIRED_SUBSTRINGS = (
    "URLSearchParams",
    "SAFE_PARAM",
    "SAFE_PARAM.test(",
    "params.get('intent')",
    "params.get('type')",
    "params.get('src')",
    "params.get('utm_source')",
    "INTENT_TO_TYPE[intent]",
    "track('landing_prefill'",
    "did_radio",
    "did_text",
    "try {",
    "catch (_)",
)


def _iife_body(html: str) -> str | None:
    idx = html.find(IIFE_MARKER)
    if idx < 0:
        return None
    start = html.find("(function () {", idx)
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(html)):
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return html[start:i + 1]
    return None


def check(html: str) -> list[str]:
    errors: list[str] = []
    if IIFE_MARKER not in html:
        errors.append(f"index.html missing IIFE marker {IIFE_MARKER!r}")
        return errors
    body = _iife_body(html)
    if body is None:
        errors.append("URL-param IIFE marker present but block unextractable (brace balance?)")
        return errors
    for needle in REQUIRED_SUBSTRINGS:
        if needle not in body:
            errors.append(f"URL-param IIFE missing substring {needle!r}")
    if "SAFE_PARAM" in body:
        m = re.search(r"SAFE_PARAM\s*=\s*(/[^/]+/[a-z]*)", body)
        if not m:
            errors.append("SAFE_PARAM not declared as regex literal")
        else:
            pat = m.group(1)
            if "^" not in pat or "$" not in pat:
                errors.append(f"SAFE_PARAM regex {pat!r} not anchored with ^ and $")
            if ".*" in pat or ".+" in pat:
                errors.append(f"SAFE_PARAM regex {pat!r} contains wildcard (must be char class)")
    if re.search(r"querySelector\([^)]*params\.get\(", body):
        errors.append("querySelector receives raw params.get(...) — SAFE_PARAM bypassed")
    try_idx = body.find("try {")
    url_idx = body.find("URLSearchParams")
    if try_idx >= 0 and url_idx >= 0 and try_idx > url_idx:
        errors.append("URLSearchParams parse not inside try/catch — malformed URL breaks page")
    return errors


def _selftest(html: str) -> int:
    baseline = check(html)
    if baseline:
        print("SELFTEST ABORT: baseline fails check():", file=sys.stderr)
        for e in baseline:
            print(f"  {e}", file=sys.stderr)
        return 1
    cases: list[tuple[str, str, str]] = [
        ("URLSearchParams stripped", html.replace("URLSearchParams", "NopeParams"), "URLSearchParams"),
        ("landing_prefill event renamed", html.replace("track('landing_prefill'", "track('nope_prefill'"), "track('landing_prefill'"),
        ("utm_source dropped", html.replace("params.get('utm_source')", "params.get('nope')"), "utm_source"),
        ("SAFE_PARAM call stripped", html.replace("SAFE_PARAM.test(v)", "true"), "SAFE_PARAM.test("),
        ("IIFE marker removed", html.replace(IIFE_MARKER, "removed marker"), IIFE_MARKER),
        ("INTENT_TO_TYPE lookup killed", html.replace("INTENT_TO_TYPE[intent]", "null"), "INTENT_TO_TYPE[intent]"),
    ]
    failures: list[str] = []
    for label, mutated, needle in cases:
        if mutated == html:
            failures.append(f"{label}: mutation no-op")
            continue
        errs = check(mutated)
        if not errs:
            failures.append(f"{label}: mutation slipped through")
            continue
        if not any(needle in e for e in errs):
            failures.append(f"{label}: wrong error surfaced (want {needle!r}, got {errs!r})")
    if failures:
        print("SELFTEST FAIL:", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    print(f"SELFTEST OK ({len(cases)} mutations, all caught)")
    return 0


def main(argv: list[str]) -> int:
    html = INDEX.read_text(encoding="utf-8")
    if "--selftest" in argv:
        return _selftest(html)
    errs = check(html)
    if errs:
        for e in errs:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("OK: URL-param prefill IIFE present, SAFE_PARAM gated, landing_prefill emitted.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
