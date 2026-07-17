"""
Conversion IIFE contract test.

Why: `index.html` carries a hand-rolled `data-intent` → `projectType` mapping
in the conversion IIFE (see CONVERSION_STANDARDS.md §§ 2-4). It is the money
path — CTA click prefills the intake radio + textarea, then pushes `cta_click`
to `window.dataLayer` for analytics attribution.

A silent regression here — a renamed slug, a removed radio value, a mapping
that drifts out of sync — kills conversion attribution and prefill without a
Lighthouse-visible signal. This stdlib-only smoke locks the contract.

Cross-checks:
  1. Every `INTENT_TO_TYPE[key] = value` in the IIFE has a matching
     `<input name="projectType" value="value">` radio in the HTML.
  2. Every `data-intent="service:..."` / `data-intent="portfolio:..."` on an
     `<a>` in the HTML has an entry in `INTENT_TO_TYPE`.
  3. Every `INTENT_TO_TYPE` key is used by at least one CTA (no dead entries
     — a dead mapping is either a typo or a stealth-removed CTA).
  4. Every `projectType` radio value is a target of at least one mapping
     (an orphan radio value is either dead code or a missing CTA for a
     service the site actually offers).
  5. The dataLayer push and adapter monkey-patch strings are present — the
     attribution loop is wired end-to-end.
  6. (tick 19) Every lane-page deep-link CTA `href="/?intent=service:XYZ&src=..."`
     on the three lane pages (home-repair / commercial-industrial /
     residential-construction) has its `intent=` value present in
     `INTENT_TO_TYPE`, and every deep-link carries a `src=` attribution
     param. A typo like `service:custom-home` → `service:custom-house`
     shipped on a lane page silently no-ops the URL-param prefill IIFE
     (SAFE_PARAM passes, `INTENT_TO_TYPE[intent]` is undefined) — the
     visitor lands on `/#contact` with no radio checked, no textarea seed,
     and no attribution. No other test catches this cross-file drift.
  7. (tick 20d) Every lane deep-link's `src=` value on lane page P equals
     LANE_SRC_MAP[P]. Before this: `src=` merely had to be non-empty, so a
     copy-paste of a service row from commercial-industrial.html into
     home-repair.html that leaves `src=commercial-industrial-lane` in place
     ships silently and mislabels every home-repair intake as commercial
     in the funnel view — the lane-attribution loop (tick 27 Formspree +
     tick 20c dataLayer) points at the wrong lane and every A/B decision
     downstream is based on a poisoned split.
  8. (tick 20d) Each lane page carries ≥ MIN_LANE_CTAS deep-link CTAs so a
     slow gutting of the funnel (delete one service row per session) can't
     ship silently — the tick-19 "at least one" floor is too permissive to
     catch drift below the shipped counts of 4-6 per lane.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "index.html"
# Shared money-path JS (extracted from index.html 2026-07-17). The conversion
# IIFE + INTENT_TO_TYPE + analytics adapter live here now; the DOM surface
# (radios, data-intent CTAs) stays in index.html — so the contract is checked
# against the concatenation of both files.
BIG7_JS = REPO_ROOT / "big7.js"
LANE_PAGES = (
    "home-repair.html",
    "commercial-industrial.html",
    "residential-construction.html",
)

# The single canonical attribution slug per lane page. The dataLayer + Formspree
# funnel splits on this string exactly; a lane page shipping with the wrong
# slug (typo, or copy-paste from a sibling lane) collapses two lanes into one
# in every downstream funnel view. Locking the page↔slug pair here means a
# rename anywhere requires touching the test — grep-scannable, review-visible.
LANE_SRC_MAP: dict[str, str] = {
    "home-repair.html": "home-repair-lane",
    "residential-construction.html": "residential-construction-lane",
}

# Lane pages rebuilt as full destination pages (2026-07-17 two-path
# restructure): each carries its OWN intake form, so service CTAs are
# on-page `href="#contact"` + `data-intent` (no more `/?intent=` round-trip
# through the homepage). The contract for these pages:
#   1. >= MIN_LANE_CTAS on-page `data-intent="service:*|portfolio:*"` CTAs,
#      every intent present in INTENT_TO_TYPE (else big7.js prefill no-ops).
#   2. A hidden `<input name="source" value="<slug>">` whose default equals
#      this map's slug — the Formspree lane-attribution replacement for the
#      old per-deep-link `src=` param.
REBUILT_LANE_SRC: dict[str, str] = {
    "commercial-industrial.html": "commercial-industrial-page",
}

# Floor for lane-page deep-link CTAs. Shipped counts are 4-6 per lane
# (2026-07-13); floor of 3 catches a slow gutting below shipped level while
# leaving room for a lane page that legitimately trims to a shorter service
# menu. Tighten to 4 the next time the lane pages are re-audited.
MIN_LANE_CTAS = 3

INTENT_TO_TYPE_BLOCK_RE = re.compile(
    r"const\s+INTENT_TO_TYPE\s*=\s*\{(?P<body>[^}]*)\}",
    re.DOTALL,
)
MAPPING_ENTRY_RE = re.compile(
    r"""['"](?P<key>[a-z0-9:_\-]+)['"]\s*:\s*['"](?P<val>[a-z0-9\-_]+)['"]""",
    re.IGNORECASE,
)
PROJECT_TYPE_RADIO_RE = re.compile(
    r'<input\s+type="radio"\s+name="projectType"\s+value="(?P<val>[^"]+)"',
    re.IGNORECASE,
)
DATA_INTENT_RE = re.compile(
    r'data-intent="(?P<intent>(?:service|portfolio):[a-z0-9\-]+)"',
    re.IGNORECASE,
)
# Lane-page deep-link CTAs: href="/?intent=service:XYZ&amp;src=lane#contact" or
# href="/?src=lane#contact" (bottom-of-page primary "Request a bid" without an
# intent-specific slug). Query string ends at '"' or '#'.
LANE_DEEP_LINK_RE = re.compile(
    r'href="/\?(?P<qs>[^"#]*)(?:#[^"]*)?"',
    re.IGNORECASE,
)

# Substrings that must appear in the IIFE + adapter for the funnel to work.
# The `track('...',` forms are the actual call sites — checking the bare event
# name is fooled by a comment mention of the same string, so we require the
# code-path expression.
REQUIRED_SUBSTRINGS = (
    "dataLayer",
    "track('cta_click'",
    "track('intake_submit'",
    "PREFILL_MARK",
    "window.gtag",
    "window.plausible",
)


def parse_mapping(html: str) -> tuple[dict[str, str], list[str]]:
    """Return (INTENT_TO_TYPE dict, errors)."""
    errors: list[str] = []
    m = INTENT_TO_TYPE_BLOCK_RE.search(html)
    if not m:
        errors.append("could not find `const INTENT_TO_TYPE = { ... }` block in index.html+big7.js")
        return {}, errors

    body = m.group("body")
    mapping: dict[str, str] = {}
    for em in MAPPING_ENTRY_RE.finditer(body):
        key = em.group("key")
        val = em.group("val")
        if key in mapping and mapping[key] != val:
            errors.append(
                f"INTENT_TO_TYPE has duplicate key {key!r} with conflicting values "
                f"{mapping[key]!r} vs {val!r}"
            )
        mapping[key] = val

    if not mapping:
        errors.append("INTENT_TO_TYPE block was found but parsed zero entries")
    return mapping, errors


def parse_radios(html: str) -> set[str]:
    return {m.group("val") for m in PROJECT_TYPE_RADIO_RE.finditer(html)}


def parse_intents(html: str) -> set[str]:
    return {m.group("intent") for m in DATA_INTENT_RE.finditer(html)}


def parse_lane_deep_links(html: str) -> list[dict[str, str]]:
    """Return one dict per href="/?..." lane deep-link CTA.

    Each dict has: {"intent": str, "src": str, "raw": str}. Absent params
    come back as "". `raw` is the whole href match, used in error messages
    so a failure names the exact HTML the maintainer needs to fix.
    """
    results: list[dict[str, str]] = []
    for m in LANE_DEEP_LINK_RE.finditer(html):
        qs = m.group("qs").replace("&amp;", "&")
        intent = ""
        src = ""
        for pair in qs.split("&"):
            if "=" not in pair:
                continue
            k, v = pair.split("=", 1)
            if k == "intent":
                intent = v
            elif k == "src":
                src = v
        results.append({"intent": intent, "src": src, "raw": m.group(0)})
    return results


def check_lane_deep_links(
    mapping: dict[str, str],
    lane_html: str,
    lane_name: str,
    expected_src: str | None = None,
    min_ctas: int = 1,
) -> list[str]:
    """Validate lane-page CTA deep-links against the INTENT_TO_TYPE mapping.

    - At least `min_ctas` deep-link href="/?..." must be present (else the
      lane page ships a gutted or missing funnel back to the intake form).
    - Every deep-link's `intent=` value (when present) must be a key in
      the mapping — else URL-param prefill silently no-ops.
    - Every deep-link must carry `src=` — the tick-27 lane-attribution loop
      needs a source slug on every lane CTA to survive Formspree round-trip.
    - When `expected_src` is provided, every deep-link's `src=` value must
      equal it (tick-20d cross-lane paste lock).
    """
    errors: list[str] = []
    links = parse_lane_deep_links(lane_html)
    if len(links) < min_ctas:
        errors.append(
            f"{lane_name}: only {len(links)} lane deep-link href=\"/?...\" "
            f"CTA(s) found, below floor of {min_ctas} — slow gutting of the "
            f"funnel is shipping without a signal"
        )
        if not links:
            return errors
    for link in links:
        if link["intent"] and link["intent"] not in mapping:
            errors.append(
                f"{lane_name}: deep-link intent={link['intent']!r} not in "
                f"INTENT_TO_TYPE — URL-param prefill will silently no-op on "
                f"landing ({link['raw']})"
            )
        if not link["src"]:
            errors.append(
                f"{lane_name}: deep-link missing src= attribution param "
                f"({link['raw']}) — lane attribution collapses at Formspree"
            )
        elif expected_src is not None and link["src"] != expected_src:
            errors.append(
                f"{lane_name}: deep-link src={link['src']!r} does not match "
                f"expected lane slug {expected_src!r} — copy-paste from a "
                f"sibling lane will mislabel every intake in the funnel "
                f"({link['raw']})"
            )
    return errors


HIDDEN_SOURCE_RE = re.compile(
    r'<input\s+type="hidden"\s+name="source"\s+value="(?P<val>[^"]*)"',
    re.IGNORECASE,
)


def check_rebuilt_lane(
    mapping: dict[str, str],
    lane_html: str,
    lane_name: str,
    expected_src: str,
    min_ctas: int = 1,
) -> list[str]:
    """Validate a rebuilt destination lane page (own form, on-page CTAs).

    - At least `min_ctas` on-page `data-intent` CTAs (service:*/portfolio:*)
      must exist, each with its intent in INTENT_TO_TYPE — else the big7.js
      click-prefill silently no-ops on this page.
    - The page's hidden `source` input default must equal `expected_src` so
      every Formspree intake from this page carries lane attribution without
      relying on a `?src=` param.
    """
    errors: list[str] = []
    intents = parse_intents(lane_html)
    if len(intents) < min_ctas:
        errors.append(
            f"{lane_name}: only {len(intents)} on-page data-intent CTA(s) found, "
            f"below floor of {min_ctas} — slow gutting of the funnel is shipping "
            f"without a signal"
        )
    for intent in sorted(intents):
        if intent not in mapping:
            errors.append(
                f"{lane_name}: CTA data-intent={intent!r} not in INTENT_TO_TYPE — "
                f"big7.js prefill will silently no-op on click"
            )
    src_matches = HIDDEN_SOURCE_RE.findall(lane_html)
    if not src_matches:
        errors.append(
            f"{lane_name}: no hidden <input name=\"source\"> found — every intake "
            f"from this page ships with blank lane attribution"
        )
    elif src_matches[0] != expected_src:
        errors.append(
            f"{lane_name}: hidden source default {src_matches[0]!r} does not match "
            f"expected lane slug {expected_src!r} — copy-paste from a sibling lane "
            f"will mislabel every intake in the funnel"
        )
    return errors


def check(html: str) -> tuple[list[str], dict[str, str], set[str], set[str]]:
    """Return (errors, mapping, radios, intents). Empty errors == contract holds."""
    errors: list[str] = []

    mapping, map_errs = parse_mapping(html)
    errors.extend(map_errs)

    radios = parse_radios(html)
    if not radios:
        errors.append('no `<input type="radio" name="projectType" value="...">` radios found')

    intents = parse_intents(html)
    if not intents:
        errors.append('no `data-intent="service:*"` or `data-intent="portfolio:*"` CTAs found')

    for key, val in mapping.items():
        if val not in radios:
            errors.append(
                f"INTENT_TO_TYPE[{key!r}] -> {val!r} but no projectType radio "
                f"carries value={val!r} (radio values: {sorted(radios)})"
            )

    for intent in intents:
        if intent not in mapping:
            errors.append(
                f"CTA carries data-intent={intent!r} but INTENT_TO_TYPE has no entry — "
                f"click will not prefill the radio (attribution still fires)"
            )

    for key in mapping:
        if key not in intents:
            errors.append(
                f"INTENT_TO_TYPE[{key!r}] is defined but no CTA uses data-intent={key!r} "
                f"— dead mapping, either the CTA was removed or the slug drifted"
            )

    mapped_targets = set(mapping.values())
    for val in radios:
        if val not in mapped_targets:
            errors.append(
                f'projectType radio value={val!r} exists but no INTENT_TO_TYPE entry '
                f"points at it — either the radio is dead or a CTA is missing for the "
                f"service it represents"
            )

    for needle in REQUIRED_SUBSTRINGS:
        if needle not in html:
            errors.append(f"index.html+big7.js is missing required attribution substring: {needle!r}")

    return errors, mapping, radios, intents


def _selftest(html: str) -> int:
    """Mutate the golden HTML 8 known-broken ways; each mutation MUST fail check().

    A regression here means the test would silently pass on broken HTML — the
    exact class of failure this contract exists to prevent. Each case names the
    error substring the check MUST surface so we don't just count failures — we
    prove the *right* error fires for the *right* break.
    """
    baseline_errors, mapping, radios, intents = check(html)
    if baseline_errors:
        print("SELFTEST ABORT: baseline HTML already fails check() — fix that first:", file=sys.stderr)
        for e in baseline_errors:
            print(f"  {e}", file=sys.stderr)
        return 1
    if not mapping or not radios or not intents:
        print("SELFTEST ABORT: baseline parse returned empty sets", file=sys.stderr)
        return 1

    # Pick concrete keys/values from the live HTML so the mutations bite something real.
    a_key = next(iter(mapping))
    a_val = mapping[a_key]
    a_intent = next(iter(intents))
    a_radio = next(iter(radios))

    cases: list[tuple[str, str, str]] = [
        # (label, mutated_html, error_substring_required)
        (
            "radio value removed (mapping target orphaned)",
            html.replace(
                f'name="projectType" value="{a_val}"',
                f'name="projectType" value="{a_val}-REMOVED"',
                1,
            ),
            f"-> {a_val!r} but no projectType radio",
        ),
        (
            "mapping entry deleted (CTA has no prefill)",
            re.sub(
                rf"""['"]{re.escape(a_intent)}['"]\s*:\s*['"][^'"]+['"]\s*,?""",
                "",
                html,
                count=1,
            ),
            f"data-intent={a_intent!r} but INTENT_TO_TYPE has no entry",
        ),
        (
            "CTA intent removed (mapping entry becomes dead code)",
            html.replace(f'data-intent="{a_key}"', 'data-intent="stealth-removed"'),
            f"INTENT_TO_TYPE[{a_key!r}] is defined but no CTA uses",
        ),
        (
            "radio orphaned (no CTA for a real service)",
            html.replace(
                f'name="projectType" value="{a_radio}"',
                f'name="projectType" value="{a_radio}-orphan-xyz"',
                1,
            ),
            "-orphan-xyz' exists but no INTENT_TO_TYPE entry",
        ),
        (
            "dataLayer stripped (analytics dead)",
            html.replace("dataLayer", "DEADLAYER"),
            "'dataLayer'",
        ),
        (
            "cta_click track() call removed",
            html.replace("track('cta_click'", "track('nope_click'"),
            "track('cta_click'",
        ),
        (
            "gtag adapter monkey-patch stripped",
            html.replace("window.gtag", "window.nope_gtag"),
            "window.gtag",
        ),
        (
            "INTENT_TO_TYPE block deleted entirely",
            INTENT_TO_TYPE_BLOCK_RE.sub("const REMOVED_MAPPING = {}", html, count=1),
            "could not find `const INTENT_TO_TYPE",
        ),
    ]

    failures: list[str] = []
    for label, mutated, needle in cases:
        if mutated == html:
            failures.append(f"{label}: mutation was a no-op (replace did not match)")
            continue
        errs, *_ = check(mutated)
        if not errs:
            failures.append(f"{label}: mutation slipped through — check() returned no errors")
            continue
        if not any(needle in e for e in errs):
            failures.append(
                f"{label}: mutation was caught but the error did not mention {needle!r}. "
                f"Got: {errs}"
            )

    if failures:
        for f in failures:
            print(f"SELFTEST FAIL: {f}", file=sys.stderr)
        return 1

    # Lane-page deep-link contract mutations — same doctrine, applied to the
    # cross-file surface the tick-19 extension covers. Baseline is a minimal
    # lane HTML that mirrors the real lane-page CTA structure.
    good_intent = a_key if a_key.startswith("service:") else next(
        (k for k in mapping if k.startswith("service:")), a_key
    )
    # Lane baseline: MIN_LANE_CTAS deep-links (service rows) + 1 bottom CTA,
    # all carrying the canonical `lane-selftest` slug. Sized so the mutation
    # that removes one CTA still leaves MIN_LANE_CTAS-1 (below floor) and
    # trips the count check.
    lane_row_snippet = (
        f'<a class="service-row" href="/?intent={good_intent}'
        f'&amp;src=lane-selftest#contact">row</a>\n'
    )
    lane_baseline = (
        lane_row_snippet * MIN_LANE_CTAS
        + f'<a class="btn-accent" href="/?src=lane-selftest#contact">Request a bid</a>\n'
    )
    lane_baseline_errs = check_lane_deep_links(
        mapping, lane_baseline, "lane-baseline",
        expected_src="lane-selftest",
        min_ctas=MIN_LANE_CTAS,
    )
    if lane_baseline_errs:
        print("SELFTEST ABORT: lane baseline itself fails:", file=sys.stderr)
        for e in lane_baseline_errs:
            print(f"  {e}", file=sys.stderr)
        return 1

    lane_cases: list[tuple[str, str, str]] = [
        (
            "lane deep-link intent slug drifted (typo — silent prefill no-op)",
            lane_baseline.replace(good_intent, f"{good_intent}-typo"),
            f"{good_intent}-typo' not in INTENT_TO_TYPE",
        ),
        (
            "lane deep-link src= param missing (lane attribution collapses)",
            lane_baseline.replace("&amp;src=lane-selftest", ""),
            "missing src= attribution param",
        ),
        (
            "lane page ships zero deep-link CTAs (funnel broken)",
            "<p>lane page with no deep-links</p>",
            "below floor of",
        ),
        (
            "lane deep-link src= drifts to a sibling lane slug (cross-lane paste)",
            lane_baseline.replace("src=lane-selftest", "src=some-other-lane"),
            "does not match expected lane slug 'lane-selftest'",
        ),
        (
            "lane page gutted to below MIN_LANE_CTAS (slow funnel decay)",
            # Keep only the bottom btn-accent CTA — well below the floor.
            f'<a class="btn-accent" href="/?src=lane-selftest#contact">Request a bid</a>\n',
            f"below floor of {MIN_LANE_CTAS}",
        ),
    ]

    lane_failures: list[str] = []
    for label, mutated, needle in lane_cases:
        if mutated == lane_baseline:
            lane_failures.append(f"{label}: mutation was a no-op")
            continue
        errs = check_lane_deep_links(
            mapping, mutated, "lane-mutation",
            expected_src="lane-selftest",
            min_ctas=MIN_LANE_CTAS,
        )
        if not errs:
            lane_failures.append(f"{label}: mutation slipped through")
            continue
        if not any(needle in e for e in errs):
            lane_failures.append(
                f"{label}: caught but wrong error — did not mention {needle!r}. "
                f"Got: {errs}"
            )

    if lane_failures:
        for f in lane_failures:
            print(f"SELFTEST FAIL: {f}", file=sys.stderr)
        return 1

    # Rebuilt-lane contract mutations (2026-07-17 two-path restructure) —
    # destination pages with their own form + on-page data-intent CTAs.
    distinct_intents = [k for k in mapping if k.startswith(("service:", "portfolio:"))][:MIN_LANE_CTAS]
    if len(distinct_intents) < MIN_LANE_CTAS:
        print("SELFTEST ABORT: mapping has too few intents for rebuilt-lane baseline", file=sys.stderr)
        return 1
    rebuilt_baseline = (
        "".join(
            f'<a href="#contact" class="service-row" data-intent="{k}">row</a>\n'
            for k in distinct_intents
        )
        + '<input type="hidden" name="source" value="lane-selftest-page" />\n'
    )
    rebuilt_baseline_errs = check_rebuilt_lane(
        mapping, rebuilt_baseline, "rebuilt-baseline",
        expected_src="lane-selftest-page", min_ctas=MIN_LANE_CTAS,
    )
    if rebuilt_baseline_errs:
        print("SELFTEST ABORT: rebuilt-lane baseline itself fails:", file=sys.stderr)
        for e in rebuilt_baseline_errs:
            print(f"  {e}", file=sys.stderr)
        return 1

    rebuilt_cases: list[tuple[str, str, str]] = [
        (
            "rebuilt-lane CTA intent typo'd (big7.js prefill no-ops)",
            rebuilt_baseline.replace(distinct_intents[0], f"{distinct_intents[0]}-typo", 1),
            "not in INTENT_TO_TYPE",
        ),
        (
            "rebuilt-lane hidden source input deleted (attribution goes blank)",
            re.sub(r'<input\s+type="hidden"\s+name="source"[^>]*>', "", rebuilt_baseline),
            'no hidden <input name="source">',
        ),
        (
            "rebuilt-lane hidden source drifts to a sibling slug (cross-lane paste)",
            rebuilt_baseline.replace('value="lane-selftest-page"', 'value="some-other-page"'),
            "does not match expected lane slug 'lane-selftest-page'",
        ),
        (
            "rebuilt-lane gutted below MIN_LANE_CTAS (slow funnel decay)",
            f'<a href="#contact" data-intent="{distinct_intents[0]}">row</a>\n'
            '<input type="hidden" name="source" value="lane-selftest-page" />\n',
            f"below floor of {MIN_LANE_CTAS}",
        ),
    ]
    rebuilt_failures: list[str] = []
    for label, mutated, needle in rebuilt_cases:
        if mutated == rebuilt_baseline:
            rebuilt_failures.append(f"{label}: mutation was a no-op")
            continue
        errs = check_rebuilt_lane(
            mapping, mutated, "rebuilt-mutation",
            expected_src="lane-selftest-page", min_ctas=MIN_LANE_CTAS,
        )
        if not errs:
            rebuilt_failures.append(f"{label}: mutation slipped through")
            continue
        if not any(needle in e for e in errs):
            rebuilt_failures.append(
                f"{label}: caught but wrong error — did not mention {needle!r}. "
                f"Got: {errs}"
            )
    if rebuilt_failures:
        for f in rebuilt_failures:
            print(f"SELFTEST FAIL: {f}", file=sys.stderr)
        return 1

    total = len(cases) + len(lane_cases) + len(rebuilt_cases)
    print(
        f"SELFTEST OK: {total} broken inputs all caught with the expected error "
        f"({len(cases)} mapping/attribution + {len(lane_cases)} lane deep-link)."
    )
    return 0


def main(argv: list[str]) -> int:
    for path in (INDEX, BIG7_JS):
        if not path.exists():
            print(f"FAIL: {path} not found", file=sys.stderr)
            return 1

    html = INDEX.read_text(encoding="utf-8") + "\n" + BIG7_JS.read_text(encoding="utf-8")

    if "--selftest" in argv:
        return _selftest(html)

    errors, mapping, radios, intents = check(html)

    lane_link_count = 0
    for lane in LANE_PAGES:
        lane_path = REPO_ROOT / lane
        if not lane_path.exists():
            errors.append(f"{lane}: not found at {lane_path}")
            continue
        lane_html = lane_path.read_text(encoding="utf-8")
        if lane in REBUILT_LANE_SRC:
            # Rebuilt destination page: own form + on-page data-intent CTAs.
            errors.extend(check_rebuilt_lane(
                mapping, lane_html, lane,
                expected_src=REBUILT_LANE_SRC[lane],
                min_ctas=MIN_LANE_CTAS,
            ))
            lane_link_count += len(parse_intents(lane_html))
            continue
        expected_src = LANE_SRC_MAP.get(lane)
        if expected_src is None:
            errors.append(
                f"{lane}: no entry in LANE_SRC_MAP — add the canonical "
                f"attribution slug for this lane page"
            )
        lane_errors = check_lane_deep_links(
            mapping, lane_html, lane,
            expected_src=expected_src,
            min_ctas=MIN_LANE_CTAS,
        )
        errors.extend(lane_errors)
        lane_link_count += len(parse_lane_deep_links(lane_html))

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(
        f"OK: {len(mapping)} INTENT_TO_TYPE entries, {len(intents)} CTA intents, "
        f"{len(radios)} projectType radios — contract holds; attribution loop wired. "
        f"{lane_link_count} lane CTA(s) across {len(LANE_PAGES)} lane page(s): "
        f"{len(REBUILT_LANE_SRC)} rebuilt page(s) carry on-page data-intent CTAs + "
        f"hidden source slug; legacy pages carry /?intent deep-links per "
        f"LANE_SRC_MAP (floor {MIN_LANE_CTAS} CTAs per lane)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
