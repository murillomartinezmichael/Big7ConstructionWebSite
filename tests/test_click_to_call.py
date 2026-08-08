"""
Click-to-call + sticky mobile call bar contract.

Why: the 2026-07-19 SiteAudit 30-point run graded the live site B (85/100)
with three code-side lead-leak findings on the call path: tap_target_size
FAIL (the header tel: link measured 17px — WCAG 2.5.8 wants 24, Google
wants 48), click_to_call WARN (phone text above the fold, but no tappable
tel: anchor there on mobile), and sticky_mobile_cta WARN (>2-viewport
pages with no floating call CTA — research: the cheapest lead bump for
contractor sites). The fixes are pure CSS/markup, which means a future
palette refactor or section rewrite could silently strip any of them and
no other suite would notice: test_form.py locks tel:<->JSON-LD digit
agreement, test_a11y_baseline.py locks reduced-motion presence, but
nothing locked WHERE a tel: link lives or how big its hit box is.

Contract (per page — index + both lanes):
  1. A tel: anchor exists in the header region (source order before
     `<main`) — the above-fold phone number is itself tappable.
  2. The small header tel: link's CSS rule (`.nav-phone` on index,
     `.top-links a[href^="tel:"]` on the lanes) grows the hit box to
     >=48px: vertical padding >= 15px mirrored by an equal negative
     margin (pad + ~17px line box + pad >= 48 without moving layout).
  3. A `<nav class="call-bar">` with a non-empty aria-label carries a
     tel: anchor AND an intake link (`href="#contact"`, `data-intent`
     in the `bid:` namespace so big7.js fires cta_click attribution).
     The `#contact` target id exists on the page.
  4. The call-bar CSS: hidden by default, then inside a single
     `@media (max-width: 768px)` block it is `position: fixed` +
     `bottom: 0`, its anchors carry `min-height: 48px`, and `body`
     gets a `padding-bottom` so the bar never covers page content.
  5. Any `animation: call-bar-in` lives ONLY inside a
     `prefers-reduced-motion: no-preference` media query — vestibular
     users never see the entrance slide.
  6. Every tel: href on the page carries the same digits (a call bar
     dialing a different number than the header would be invisible to
     every per-surface check).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGETS = (
    REPO_ROOT / "index.html",
    REPO_ROOT / "commercial-industrial.html",
    REPO_ROOT / "residential-construction.html",
)

TEL_HREF_RE = re.compile(r'href="tel:(?P<num>[^"]+)"', re.IGNORECASE)
CALL_BAR_NAV_RE = re.compile(
    r'<nav\b(?P<attrs>[^>]*\bclass="[^"]*\bcall-bar\b[^"]*"[^>]*)>(?P<body>.*?)</nav>',
    re.IGNORECASE | re.DOTALL,
)
ARIA_LABEL_RE = re.compile(r'\baria-label="(?P<label>[^"]*)"', re.IGNORECASE)
INTAKE_ANCHOR_RE = re.compile(
    r'<a\b[^>]*\bhref="#contact"[^>]*>', re.IGNORECASE
)
DATA_INTENT_RE = re.compile(r'\bdata-intent="(?P<intent>[^"]+)"', re.IGNORECASE)

# Header tel: hit-box rule — `.nav-phone` (index) or the attribute-selector
# form the lane pages use. Body captured up to the rule's closing brace
# (rule bodies here never nest).
HIT_RULE_RE = re.compile(
    r'(?:\.nav-phone|\.top-links\s+a\[href\^="tel:"\])\s*'
    r'\{(?P<body>[^{}]*)\}',
)
PADDING_RE = re.compile(r'padding:\s*(?P<v>\d+)px')
NEG_MARGIN_RE = re.compile(r'margin:\s*-(?P<v>\d+)px')

MIN_HIT_PAD = 15  # 2*15px + a ~17px line box >= 47-48px hit box


def _media_blocks(css: str) -> list[tuple[str, str]]:
    """Return (condition, body) for every top-level @media block.

    Brace-walked (not regexed) because the call-bar block nests rules and
    a keyframes at-rule — a lazy `.*?` would stop at the first `}`.
    """
    blocks: list[tuple[str, str]] = []
    i = 0
    while True:
        at = css.find("@media", i)
        if at == -1:
            return blocks
        brace = css.find("{", at)
        if brace == -1:
            return blocks
        cond = css[at + len("@media"):brace].strip()
        depth = 1
        j = brace + 1
        while j < len(css) and depth:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
            j += 1
        blocks.append((cond, css[brace + 1:j - 1]))
        i = j


def check(html: str, label: str) -> list[str]:
    errors: list[str] = []

    # (1) tappable phone in the header region (before <main>).
    main_at = html.lower().find("<main")
    head_region = html[:main_at] if main_at != -1 else html
    # JSON-LD `telephone` fields are not anchors — only count href="tel:".
    if not TEL_HREF_RE.search(head_region):
        errors.append(
            f"{label}: no tel: anchor before <main> — the above-fold phone "
            f"number is not tappable (SiteAudit click_to_call)"
        )

    # (2) header tel: hit-box rule >= 48px via padding + mirrored negative
    # margin. Rules without padding (e.g. the display toggle at >=769px)
    # are skipped.
    sized = False
    for m in HIT_RULE_RE.finditer(html):
        body = m.group("body")
        pad = PADDING_RE.search(body)
        neg = NEG_MARGIN_RE.search(body)
        if not pad:
            continue
        if int(pad.group("v")) >= MIN_HIT_PAD and neg and pad.group("v") == neg.group("v"):
            sized = True
            break
    if not sized:
        errors.append(
            f"{label}: no header tel: hit-box rule with vertical padding >= "
            f"{MIN_HIT_PAD}px mirrored by an equal negative margin — the "
            f"phone link's tap target shrinks back to its ~17px line box "
            f"(SiteAudit tap_target_size)"
        )

    # (3) sticky call bar markup.
    bar = CALL_BAR_NAV_RE.search(html)
    if not bar:
        errors.append(
            f"{label}: no <nav class=\"call-bar\"> — mobile loses the "
            f"floating Call / Get-a-bid bar (SiteAudit sticky_mobile_cta)"
        )
    else:
        attrs, body = bar.group("attrs"), bar.group("body")
        aria = ARIA_LABEL_RE.search(attrs)
        if not (aria and aria.group("label").strip()):
            errors.append(
                f"{label}: call bar has no aria-label — AT users get an "
                f"unnamed navigation landmark"
            )
        if not TEL_HREF_RE.search(body):
            errors.append(
                f"{label}: call bar is missing its tel: anchor — the Call "
                f"button is the bar's whole reason to exist"
            )
        intake = INTAKE_ANCHOR_RE.search(body)
        if not intake:
            errors.append(
                f"{label}: call bar is missing an intake link to #contact — "
                f"visitors who won't phone have no bid path from the bar"
            )
        else:
            intent = DATA_INTENT_RE.search(intake.group(0))
            if not intent:
                errors.append(
                    f"{label}: call-bar intake link is missing data-intent — "
                    f"sticky-bar clicks vanish from cta_click attribution"
                )
            elif not intent.group("intent").startswith("bid:"):
                errors.append(
                    f"{label}: call-bar intake link carries "
                    f"data-intent={intent.group('intent')!r} — expected the "
                    f"`bid:` namespace (big7.js position derivation)"
                )
        if 'id="contact"' not in html:
            errors.append(
                f"{label}: call bar links #contact but no id=\"contact\" "
                f"exists on the page — the Get-a-bid button goes nowhere"
            )

    # (4) call-bar CSS inside the single non-motion max-width:768px block.
    mobile_blocks = [
        (cond, body)
        for cond, body in _media_blocks(html)
        if "max-width: 768px" in cond and "prefers-reduced-motion" not in cond
    ]
    if len(mobile_blocks) != 1:
        errors.append(
            f"{label}: expected exactly one non-motion @media (max-width: "
            f"768px) block owning the call-bar CSS, found "
            f"{len(mobile_blocks)} — the mobile-only contract is ambiguous"
        )
    else:
        mbody = mobile_blocks[0][1]
        if not re.search(r"\.call-bar\s*\{[^}]*position:\s*fixed", mbody):
            errors.append(
                f"{label}: .call-bar is not position: fixed inside the "
                f"mobile block — the bar scrolls away with the page"
            )
        if not re.search(r"\.call-bar\s*\{[^}]*bottom:\s*0", mbody):
            errors.append(
                f"{label}: .call-bar has no bottom: 0 inside the mobile "
                f"block — the bar is not pinned to the viewport bottom"
            )
        if not re.search(r"\.call-bar\s+a\s*\{[^}]*min-height:\s*48px", mbody):
            errors.append(
                f"{label}: call-bar anchors lost min-height: 48px — the tap "
                f"targets shrink below the 48px floor the bar exists to meet"
            )
        if not re.search(r"body\s*\{[^}]*padding-bottom", mbody):
            errors.append(
                f"{label}: mobile block has no body padding-bottom — the "
                f"fixed bar covers the last content section"
            )
    if ".call-bar { display: none; }" not in html:
        errors.append(
            f"{label}: missing `.call-bar {{ display: none; }}` base rule — "
            f"the mobile bar leaks onto desktop viewports"
        )

    # (5) entrance animation only under no-preference.
    for cond, body in _media_blocks(html):
        if "animation: call-bar-in" in body and \
                "prefers-reduced-motion: no-preference" not in cond:
            errors.append(
                f"{label}: `animation: call-bar-in` lives under @media "
                f"({cond}) — the entrance slide must be gated behind "
                f"prefers-reduced-motion: no-preference"
            )
    if "animation: call-bar-in" in html and not any(
        "animation: call-bar-in" in body for _, body in _media_blocks(html)
    ):
        errors.append(
            f"{label}: `animation: call-bar-in` sits outside every @media "
            f"block — reduced-motion users get the slide unconditionally"
        )

    # (6) one phone number per page.
    digits = {re.sub(r"\D", "", m.group("num")) for m in TEL_HREF_RE.finditer(html)}
    if len(digits) > 1:
        errors.append(
            f"{label}: tel: anchors dial {len(digits)} different numbers "
            f"({sorted(digits)}) — the call bar / header / footer drifted "
            f"apart"
        )

    return errors


BASELINE = """<html><head><style>
    .nav-phone {
      font-size: 14px;
      padding: 16px 10px;
      margin: -16px -10px;
    }
    @media (min-width: 769px) { .nav-phone { display: inline-block; } }
    .call-bar { display: none; }
    @media (max-width: 768px) {
      .call-bar { position: fixed; left: 0; right: 0; bottom: 0; display: flex; }
      .call-bar a { min-height: 48px; }
      body { padding-bottom: 80px; }
    }
    @media (max-width: 768px) and (prefers-reduced-motion: no-preference) {
      .call-bar { animation: call-bar-in 300ms ease-out; }
      @keyframes call-bar-in { from { transform: translateY(100%); } to { transform: translateY(0); } }
    }
</style></head><body>
<header><a href="tel:5557000007" class="nav-phone">(555) 700-0007</a></header>
<main id="main"><section id="contact">intake form</section></main>
<nav class="call-bar" aria-label="Call or request a bid">
  <a href="tel:5557000007" class="cb-call">Call (555) 700-0007</a>
  <a href="#contact" class="cb-bid" data-intent="bid:sticky">Get a bid &rarr;</a>
</nav>
</body></html>"""


def _selftest() -> int:
    baseline_errors = check(BASELINE, "baseline")
    if baseline_errors:
        print("SELFTEST ABORT: synthetic baseline fails check():", file=sys.stderr)
        for e in baseline_errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    cases: list[tuple[str, str, str]] = [
        (
            "header tel: anchor removed",
            BASELINE.replace(
                '<header><a href="tel:5557000007" class="nav-phone">(555) 700-0007</a></header>',
                "<header>(555) 700-0007</header>",
            ),
            "no tel: anchor before <main>",
        ),
        (
            "hit-box padding rule stripped",
            BASELINE.replace("padding: 16px 10px;\n      margin: -16px -10px;", ""),
            "no header tel: hit-box rule",
        ),
        (
            "hit-box padding shrunk below the floor",
            BASELINE.replace("padding: 16px 10px", "padding: 4px 10px").replace(
                "margin: -16px -10px", "margin: -4px -10px"
            ),
            "no header tel: hit-box rule",
        ),
        (
            "negative margin no longer mirrors the padding",
            BASELINE.replace("margin: -16px -10px", "margin: -2px -10px"),
            "no header tel: hit-box rule",
        ),
        (
            "call-bar nav removed entirely",
            re.sub(r'<nav class="call-bar".*?</nav>', "", BASELINE, flags=re.DOTALL),
            'no <nav class="call-bar">',
        ),
        (
            "call-bar tel: anchor dropped",
            BASELINE.replace(
                '  <a href="tel:5557000007" class="cb-call">Call (555) 700-0007</a>\n', ""
            ),
            "call bar is missing its tel: anchor",
        ),
        (
            "call-bar intake link dropped",
            BASELINE.replace(
                '  <a href="#contact" class="cb-bid" data-intent="bid:sticky">Get a bid &rarr;</a>\n',
                "",
            ),
            "missing an intake link to #contact",
        ),
        (
            "call-bar intake link lost data-intent",
            BASELINE.replace(' data-intent="bid:sticky"', ""),
            "missing data-intent",
        ),
        (
            "call-bar intake intent rebadged outside bid: namespace",
            BASELINE.replace('data-intent="bid:sticky"', 'data-intent="misc:oops"'),
            "expected the `bid:` namespace",
        ),
        (
            "position: fixed removed from the mobile block",
            BASELINE.replace("position: fixed; left: 0; right: 0; bottom: 0;", ""),
            "not position: fixed",
        ),
        (
            "48px anchor floor removed",
            BASELINE.replace(".call-bar a { min-height: 48px; }", ""),
            "lost min-height: 48px",
        ),
        (
            "body padding-bottom removed (bar covers content)",
            BASELINE.replace("body { padding-bottom: 80px; }", ""),
            "no body padding-bottom",
        ),
        (
            "display: none base rule removed (bar leaks onto desktop)",
            BASELINE.replace(".call-bar { display: none; }", ""),
            "display: none",
        ),
        (
            "entrance animation escapes the reduced-motion gate",
            BASELINE.replace(
                "@media (max-width: 768px) and (prefers-reduced-motion: no-preference)",
                "@media (max-width: 768px) and (min-width: 1px)",
            ),
            "must be gated behind prefers-reduced-motion",
        ),
        (
            "call bar dials a different number than the header",
            BASELINE.replace('href="tel:5557000007" class="cb-call"', 'href="tel:5559999999" class="cb-call"'),
            "different numbers",
        ),
    ]

    failures: list[str] = []
    for label, mutated, needle in cases:
        if mutated == BASELINE:
            failures.append(f"{label}: mutation was a no-op (replace did not match)")
            continue
        errs = check(mutated, "baseline")
        if not errs:
            failures.append(f"{label}: mutation slipped through — check() returned no errors")
            continue
        if not any(needle in e for e in errs):
            failures.append(
                f"{label}: mutation caught but no error contained {needle!r}. Got: {errs}"
            )

    if failures:
        for f in failures:
            print(f"SELFTEST FAIL: {f}", file=sys.stderr)
        return 1

    print(f"SELFTEST OK: {len(cases)} broken inputs all caught with the expected error.")
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()

    all_errors: list[str] = []
    for path in TARGETS:
        if not path.exists():
            all_errors.append(f"{path.name}: file not found")
            continue
        all_errors.extend(check(path.read_text(encoding="utf-8"), path.name))

    if all_errors:
        for e in all_errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(
        f"OK: all {len(TARGETS)} pages carry a tappable >=48px header tel: "
        f"link and a mobile-only sticky call bar (tel: + bid:* intake, "
        f"48px targets, reduced-motion-gated entrance, content padding)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
