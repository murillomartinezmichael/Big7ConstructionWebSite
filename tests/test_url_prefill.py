"""URL-param prefill contract (bio-link landing).

Money path: `?intent=service:*` / `?type=<projectType>` / `?src=<slug>` on the
landing URL prefills the intake radio + textarea. A silent break here means
every TikTok/IG/email bio click hits a blank form. Locks the IIFE shape,
SAFE_PARAM whitelist, and `landing_prefill` attribution event.

Tick 20e: the substring `"track('landing_prefill'"` was already required, but
the *payload keys* of that event were not — a refactor that shipped
`track('landing_prefill', { intent })` (dropping page/src/type/did_*) would
still pass the substring check and silently gut the lane-attribution funnel
at the dataLayer surface. `intake_submit` gained an equivalent key-set lock
in tick 20c (`test_intake_analytics.py`); this test mirrors that pattern.
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
    # `src` must land in the hidden form field, not just dataLayer — otherwise
    # Formspree receives no lane attribution and the estimator can't see which
    # bio link / lane page drove the intake.
    "did_source",
    'input[name="source"]',
    "try {",
    "catch (_)",
)

# `track('landing_prefill', { ... })` — payload literal ends at the matching `}`.
# Flat object; a single-level brace match is enough (same shape used in
# test_intake_analytics.CTA_CLICK_RE).
LANDING_PREFILL_RE = re.compile(
    r"track\(\s*'landing_prefill'\s*,\s*\{(?P<body>[^}]*)\}\s*\)",
    re.DOTALL,
)
# Extract key names from an object literal — `foo:` at a tokenish position.
PAYLOAD_KEY_RE = re.compile(r"(?:^|[,{\s])(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:")

# Every key downstream GA4/Plausible depends on to bucket lane-landing rates:
#   intent      — what the user clicked in the bio link
#   type        — the projectType that was pre-selected on the radio
#   src         — lane attribution slug (drives Formspree "source" too)
#   page        — landing page identifier (always 'home' — the IIFE only runs on `/`)
#   did_radio   — did the radio prefill actually succeed (safety metric)
#   did_text    — did the textarea prefill actually succeed
#   did_source  — did the hidden `source` input get populated (attribution success)
LANDING_PREFILL_REQUIRED = {
    "intent", "type", "src", "page",
    "did_radio", "did_text", "did_source",
}

# The form MUST carry the hidden `source` input the IIFE writes into. If a
# refactor drops the hidden field, the JS silently no-ops (querySelector returns
# null, handled) and every intake ships with blank attribution.
HIDDEN_SOURCE_INPUT_RE = re.compile(
    r'<input\s+type="hidden"\s+name="source"\s+value=""\s*/?>',
    re.IGNORECASE,
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
    if not HIDDEN_SOURCE_INPUT_RE.search(html):
        errors.append(
            'hidden <input name="source"> missing from index.html — URL-param '
            "IIFE writes into this field to persist lane attribution to Formspree"
        )
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

    # landing_prefill payload contract — parse `track('landing_prefill', {...})`
    # against the FULL html (not just the IIFE body) so a moved event that lands
    # outside the IIFE still gets counted (dupe detection stays honest).
    lp_matches = list(LANDING_PREFILL_RE.finditer(html))
    if len(lp_matches) != 1:
        errors.append(
            f"expected exactly 1 `track('landing_prefill', {{...}})` call, found "
            f"{len(lp_matches)} — a duplicate double-fires the lane-attribution event "
            f"and inflates every landing-rate metric"
        )
    if lp_matches:
        keys = {m.group("key") for m in PAYLOAD_KEY_RE.finditer(lp_matches[0].group("body"))}
        missing = LANDING_PREFILL_REQUIRED - keys
        if missing:
            errors.append(
                f"landing_prefill payload missing required key(s) {sorted(missing)} "
                f"(payload had {sorted(keys)}); the lane-attribution funnel loses "
                f"{sorted(missing)} at the dataLayer surface"
            )
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
        (
            "hidden source input deleted",
            HIDDEN_SOURCE_INPUT_RE.sub("", html, count=1),
            'hidden <input name="source">',
        ),
        (
            "did_source telemetry dropped",
            html.replace("did_source", "did_nope"),
            "did_source",
        ),
        (
            "IIFE stops writing into input[name=source]",
            html.replace('input[name="source"]', 'input[name="nope"]'),
            'input[name="source"]',
        ),
        # landing_prefill payload contract — each key downstream analytics buckets on.
        (
            "landing_prefill.page dropped (lane funnel loses landing-page identity)",
            html.replace(
                "intent: intent, type: resolvedType, src: src, page: 'home',",
                "intent: intent, type: resolvedType, src: src,",
                1,
            ),
            "landing_prefill payload missing required key(s) ['page']",
        ),
        (
            "landing_prefill.src dropped (lane attribution goes dark at dataLayer)",
            html.replace(
                "intent: intent, type: resolvedType, src: src, page: 'home',",
                "intent: intent, type: resolvedType, page: 'home',",
                1,
            ),
            "landing_prefill payload missing required key(s) ['src']",
        ),
        (
            "landing_prefill.did_source dropped (attribution-success signal lost)",
            html.replace(
                "did_radio: didRadio, did_text: didText, did_source: didSource",
                "did_radio: didRadio, did_text: didText",
                1,
            ),
            "landing_prefill payload missing required key(s) ['did_source']",
        ),
        (
            "landing_prefill.type dropped (radio-prefill success ambiguous)",
            html.replace(
                "intent: intent, type: resolvedType, src: src, page: 'home',",
                "intent: intent, src: src, page: 'home',",
                1,
            ),
            "landing_prefill payload missing required key(s) ['type']",
        ),
        (
            "landing_prefill call duplicated (double-fires every landing)",
            html.replace(
                "track('landing_prefill', {\n"
                "            intent: intent, type: resolvedType, src: src, page: 'home',\n"
                "            did_radio: didRadio, did_text: didText, did_source: didSource\n"
                "          });",
                "track('landing_prefill', {\n"
                "            intent: intent, type: resolvedType, src: src, page: 'home',\n"
                "            did_radio: didRadio, did_text: didText, did_source: didSource\n"
                "          });\n"
                "          track('landing_prefill', {\n"
                "            intent: intent, type: resolvedType, src: src, page: 'home',\n"
                "            did_radio: didRadio, did_text: didText, did_source: didSource\n"
                "          });",
                1,
            ),
            "found 2",
        ),
        (
            "landing_prefill call removed entirely (funnel entry-point invisible)",
            re.sub(r"track\('landing_prefill'\s*,\s*\{[^}]*\}\s*\)\s*;?", "", html, count=1),
            "found 0",
        ),
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
    print(
        f"OK: URL-param prefill IIFE present, SAFE_PARAM gated, landing_prefill emitted "
        f"with payload keys {sorted(LANDING_PREFILL_REQUIRED)}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
