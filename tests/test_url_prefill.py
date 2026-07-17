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
# Shared money-path JS (extracted from index.html 2026-07-17). The URL-param
# prefill IIFE lives here now; the hidden source input stays in the page HTML —
# the contract is checked against the concatenation of both files.
BIG7_JS = REPO_ROOT / "big7.js"

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
#   page        — landing page identifier (BIG7_PAGE: 'home' on `/`, the page
#                 slug on lane pages — big7.js runs on every page since 2026-07-17)
#   did_radio   — did the radio prefill actually succeed (safety metric)
#   did_text    — did the textarea prefill actually succeed
#   did_source  — did the hidden `source` input get populated (attribution success)
LANDING_PREFILL_REQUIRED = {
    "intent", "type", "src", "page",
    "did_radio", "did_text", "did_source",
}

# The lane forms carry hidden `source` inputs with non-empty defaults —
# locked by test_form.py + test_conversion.py. This test locks the JS side
# (the IIFE writes into input[name="source"]) plus the index legacy shim.

# Index legacy-URL shim (2026-07-17): /?intent=* URLs redirect to the lane
# that owns the resolved projectType. Its INTENT_TO_TYPE copy must stay in
# byte-sync with big7.js, and TYPE_TO_LANE must cover every projectType.
SHIM_MARKER = "Legacy money-URL shim"
JS_MAP_ENTRY_RE = re.compile(
    r"""['"](?P<key>[a-z0-9:_\-\.\/]+)['"]\s*:\s*['"](?P<val>[a-z0-9\-_\.\/]+)['"]""",
    re.IGNORECASE,
)


def _js_map(text: str, name: str) -> dict[str, str] | None:
    m = re.search(r"(?:var|const)\s+" + name + r"\s*=\s*\{(?P<body>[^}]*)\}", text, re.DOTALL)
    if not m:
        return None
    return {e.group("key"): e.group("val") for e in JS_MAP_ENTRY_RE.finditer(m.group("body"))}


def check_shim(index_html: str, big7_js: str) -> list[str]:
    errors: list[str] = []
    if SHIM_MARKER not in index_html:
        errors.append(f"index.html missing legacy shim marker {SHIM_MARKER!r}")
        return errors
    shim_start = index_html.find(SHIM_MARKER)
    shim = index_html[shim_start:shim_start + 4000]
    for needle in ("URLSearchParams", "SAFE_PARAM", "location.replace"):
        if needle not in shim:
            errors.append(f"legacy shim missing substring {needle!r}")
    shim_map = _js_map(shim, "INTENT_TO_TYPE")
    big7_map = _js_map(big7_js, "INTENT_TO_TYPE")
    if shim_map is None:
        errors.append("legacy shim carries no INTENT_TO_TYPE map")
    elif big7_map is None:
        errors.append("big7.js INTENT_TO_TYPE unparseable")
    elif shim_map != big7_map:
        errors.append(
            f"shim INTENT_TO_TYPE drifted from big7.js: only-in-shim="
            f"{sorted(set(shim_map.items()) - set(big7_map.items()))}, only-in-big7="
            f"{sorted(set(big7_map.items()) - set(shim_map.items()))} — a legacy "
            f"bio link would prefill one thing on the lane page and redirect on another"
        )
    lane_map = _js_map(shim, "TYPE_TO_LANE")
    if lane_map is None:
        errors.append("legacy shim carries no TYPE_TO_LANE map")
    elif big7_map is not None:
        all_types = set(big7_map.values())
        missing = all_types - set(lane_map.keys())
        if missing:
            errors.append(
                f"shim TYPE_TO_LANE missing projectType(s) {sorted(missing)} — those "
                f"legacy URLs would dead-end on the formless chooser page"
            )
        bad = {v for v in lane_map.values()
               if v not in ("/commercial-industrial.html", "/residential-construction.html")}
        if bad:
            errors.append(f"shim TYPE_TO_LANE routes to unknown page(s): {sorted(bad)}")
    return errors


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
        errors.append(f"index.html+big7.js missing IIFE marker {IIFE_MARKER!r}")
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


def _selftest(html: str, index_html: str, big7_js: str) -> int:
    baseline = check(html) + check_shim(index_html, big7_js)
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
                "intent: intent, type: resolvedType, src: src, page: BIG7_PAGE,",
                "intent: intent, type: resolvedType, src: src,",
                1,
            ),
            "landing_prefill payload missing required key(s) ['page']",
        ),
        (
            "landing_prefill.src dropped (lane attribution goes dark at dataLayer)",
            html.replace(
                "intent: intent, type: resolvedType, src: src, page: BIG7_PAGE,",
                "intent: intent, type: resolvedType, page: BIG7_PAGE,",
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
                "intent: intent, type: resolvedType, src: src, page: BIG7_PAGE,",
                "intent: intent, src: src, page: BIG7_PAGE,",
                1,
            ),
            "landing_prefill payload missing required key(s) ['type']",
        ),
        (
            "landing_prefill call duplicated (double-fires every landing)",
            html.replace(
                "track('landing_prefill', {\n"
                "        intent: intent, type: resolvedType, src: src, page: BIG7_PAGE,\n"
                "        did_radio: didRadio, did_text: didText, did_source: didSource\n"
                "      });",
                "track('landing_prefill', {\n"
                "        intent: intent, type: resolvedType, src: src, page: BIG7_PAGE,\n"
                "        did_radio: didRadio, did_text: didText, did_source: didSource\n"
                "      });\n"
                "      track('landing_prefill', {\n"
                "        intent: intent, type: resolvedType, src: src, page: BIG7_PAGE,\n"
                "        did_radio: didRadio, did_text: didText, did_source: didSource\n"
                "      });",
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

    # Legacy-shim mutations — the index-side redirect for old money URLs.
    shim_cases: list[tuple[str, str, str]] = [
        (
            "shim removed entirely (legacy bio links dead-end on formless chooser)",
            index_html.replace(SHIM_MARKER, "removed"),
            "missing legacy shim marker",
        ),
        (
            "shim location.replace stripped (no redirect fires)",
            index_html.replace("location.replace", "console.log"),
            "location.replace",
        ),
        (
            "shim INTENT_TO_TYPE drifts from big7.js (slug renamed)",
            index_html.replace("'service:custom-home':          'residential-custom',", "", 1),
            "drifted from big7.js",
        ),
        (
            "shim TYPE_TO_LANE loses a projectType (URL dead-ends)",
            index_html.replace(
                "'trades-only':          '/residential-construction.html'", "'x': '/residential-construction.html'", 1
            ),
            "TYPE_TO_LANE missing projectType",
        ),
    ]
    for label, mutated_index, needle in shim_cases:
        if mutated_index == index_html:
            failures.append(f"{label}: mutation no-op")
            continue
        errs = check_shim(mutated_index, big7_js)
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
    print(f"SELFTEST OK ({len(cases) + len(shim_cases)} mutations, all caught)")
    return 0


def main(argv: list[str]) -> int:
    index_html = INDEX.read_text(encoding="utf-8")
    big7_js = BIG7_JS.read_text(encoding="utf-8")
    html = index_html + "\n" + big7_js
    if "--selftest" in argv:
        return _selftest(html, index_html, big7_js)
    errs = check(html) + check_shim(index_html, big7_js)
    if errs:
        for e in errs:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print(
        f"OK: URL-param prefill IIFE present, SAFE_PARAM gated, landing_prefill emitted "
        f"with payload keys {sorted(LANDING_PREFILL_REQUIRED)}; index legacy shim in "
        f"sync with big7.js and TYPE_TO_LANE covers every projectType."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
