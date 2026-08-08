"""
Primary CTA attribution contract.

Why: `test_conversion.py` locks `service:*`/`portfolio:*` CTAs, but the page's
global conversion buttons — nav, hero, mobile menu, closer, and section-foot
rails — are a separate class. Before this contract they carried no
`data-intent`, so a hero click was indistinguishable in analytics from a
closer click. CONVERSION_STANDARDS.md § 4 requires `cta_click` to fire with
`intent`, `page`, and `position`; missing `data-intent` broke that outright.

Locks:
  1. Every anchor whose text is "Request a bid" carries `data-intent="bid:*"`.
  2. Every `<a class="btn btn-accent" href="#contact">` carries `data-intent`.
  3. The click IIFE derives `position` from the intent segment and emits it
     in the `cta_click` payload.
  4. Position slugs are unique across primary CTAs (no analytics collisions).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "index.html"
# Shared money-path JS (extracted from index.html 2026-07-17). The position
# derivation + cta_click payload live here now; the CTA anchors stay in the
# page HTML — the contract is checked against the concatenation of both files.
BIG7_JS = REPO_ROOT / "big7.js"

REQUEST_BID_ANCHOR_RE = re.compile(
    r'<a\b(?P<attrs>[^>]*)>\s*(?P<text>Request a bid(?:\s*(?:&rarr;|→))?)\s*</a>',
    re.IGNORECASE,
)
ACCENT_BTN_ANCHOR_RE = re.compile(
    r'<a\b(?P<attrs>[^>]*\bclass="[^"]*\bbtn\s+btn-accent\b[^"]*"[^>]*)>',
    re.IGNORECASE,
)
DATA_INTENT_ATTR_RE = re.compile(r'\bdata-intent="(?P<intent>[^"]+)"', re.IGNORECASE)
HREF_ATTR_RE = re.compile(r'\bhref="(?P<href>[^"]+)"', re.IGNORECASE)

POSITION_DERIVATION_LINE = "intent.split(':')[1]"
POSITION_IN_PAYLOAD = "position: position"


def _attr(pattern: re.Pattern[str], attrs: str) -> str | None:
    m = pattern.search(attrs)
    return m.group(1) if m else None


def check(html: str) -> tuple[list[str], list[str], list[str]]:
    errors: list[str] = []
    request_bid_intents: list[str] = []
    accent_btn_intents: list[str] = []

    matches = list(REQUEST_BID_ANCHOR_RE.finditer(html))
    if not matches:
        errors.append('no <a>Request a bid</a> anchors — primary CTA copy vanished')
    for m in matches:
        attrs = m.group("attrs")
        intent = _attr(DATA_INTENT_ATTR_RE, attrs)
        text = m.group("text").strip()
        if intent is None:
            errors.append(
                f'"{text}" anchor is missing data-intent — clicks will not fire '
                f'cta_click attribution. Attrs: {attrs.strip()!r}'
            )
            continue
        if not intent.startswith("bid:"):
            errors.append(
                f'"{text}" anchor carries data-intent={intent!r} — expected the '
                f'`bid:` namespace for the primary conversion label'
            )
            continue
        request_bid_intents.append(intent)

    for m in ACCENT_BTN_ANCHOR_RE.finditer(html):
        attrs = m.group("attrs")
        if _attr(HREF_ATTR_RE, attrs) != "#contact":
            continue
        intent = _attr(DATA_INTENT_ATTR_RE, attrs)
        if intent is None:
            errors.append(
                'accented primary button (class="btn btn-accent") anchored to '
                '#contact is missing data-intent. Attrs: ' + attrs.strip()
            )
            continue
        accent_btn_intents.append(intent)

    if POSITION_DERIVATION_LINE not in html:
        errors.append(
            f"missing position-derivation expression {POSITION_DERIVATION_LINE!r} "
            f"— cta_click payload will not carry position"
        )
    if POSITION_IN_PAYLOAD not in html:
        errors.append(
            f"missing {POSITION_IN_PAYLOAD!r} in the cta_click payload — "
            f"position field is not being emitted"
        )

    seen: dict[str, int] = {}
    for i in request_bid_intents:
        if ":" in i:
            p = i.split(":", 1)[1]
            seen[p] = seen.get(p, 0) + 1
    for p, count in seen.items():
        if count > 1:
            errors.append(
                f"primary CTA position slug {p!r} appears {count} times — "
                f"two buttons would collapse in analytics"
            )

    return errors, request_bid_intents, accent_btn_intents


def _selftest(html: str) -> int:
    baseline, req, accent = check(html)
    if baseline or not req or not accent:
        print(f"SELFTEST ABORT: baseline broken: {baseline}", file=sys.stderr)
        return 1
    a_intent = req[0]
    cases = [
        ("data-intent stripped from a Request-a-bid anchor",
         html.replace(f' data-intent="{a_intent}"', "", 1),
         "is missing data-intent"),
        ("primary CTA rebadged with non-bid namespace",
         html.replace(f'data-intent="{a_intent}"', 'data-intent="misc:oops"', 1),
         "expected the `bid:` namespace"),
        ("position derivation removed",
         html.replace(POSITION_DERIVATION_LINE, "'REMOVED'"),
         "position-derivation expression"),
        ("position field removed from payload",
         html.replace(POSITION_IN_PAYLOAD, "REMOVED_FIELD"),
         "position field is not being emitted"),
        ("two CTAs collapsed onto the same slug",
         html.replace('data-intent="bid:hero"', 'data-intent="bid:closer"', 1),
         "appears 2 times"),
    ]
    fails: list[str] = []
    for label, mutated, needle in cases:
        if mutated == html:
            fails.append(f"{label}: mutation was a no-op")
            continue
        errs, *_ = check(mutated)
        if not errs:
            fails.append(f"{label}: mutation slipped through")
            continue
        if not any(needle in e for e in errs):
            fails.append(f"{label}: wrong error, got {errs}")
    if fails:
        for f in fails:
            print(f"SELFTEST FAIL: {f}", file=sys.stderr)
        return 1
    print(f"SELFTEST OK: {len(cases)} broken inputs all caught with the expected error.")
    return 0


def main(argv: list[str]) -> int:
    for path in (INDEX, BIG7_JS):
        if not path.exists():
            print(f"FAIL: {path} not found", file=sys.stderr)
            return 1
    html = INDEX.read_text(encoding="utf-8") + "\n" + BIG7_JS.read_text(encoding="utf-8")
    if "--selftest" in argv:
        return _selftest(html)
    errors, req, accent = check(html)
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print(
        f"OK: {len(req)} primary 'Request a bid' CTAs carry bid:* intent, "
        f"{len(accent)} accented primary buttons carry data-intent; "
        f"position derivation wired."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
