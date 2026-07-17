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
  6. (2026-07-17 two-path restructure) Every lane destination page carries
     >= MIN_LANE_CTAS on-page `data-intent` CTAs whose intents exist in
     `INTENT_TO_TYPE` (else the big7.js click-prefill no-ops on that page),
     plus a hidden `source` input whose default equals REBUILT_LANE_SRC's
     slug — a copy-paste from a sibling lane that leaves the wrong slug in
     place would mislabel every intake in the funnel.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "index.html"
# Shared money-path JS (extracted from index.html 2026-07-17). The conversion
# IIFE + INTENT_TO_TYPE + analytics adapter live here; the DOM surface —
# radios and data-intent CTAs — is spread across the chooser homepage and the
# two lane destination pages (2026-07-17 two-path restructure). The mapping
# contract is therefore checked against the concatenation of ALL of them:
# every INTENT_TO_TYPE entry must have a CTA on SOME page, every mapping
# target a radio on SOME page (big7.js prefill no-ops gracefully on pages
# missing a given radio — the per-page floors are enforced separately by
# check_rebuilt_lane).
BIG7_JS = REPO_ROOT / "big7.js"
LANE_PAGES = (
    "commercial-industrial.html",
    "residential-construction.html",
)

# Lane pages are full destination pages (2026-07-17 two-path restructure;
# home-repair.html folded into the residential page and 301'd): each carries
# its OWN intake form, so service CTAs are on-page `href="#contact"` +
# `data-intent` (no more `/?intent=` round-trip through the homepage).
# The single canonical attribution slug per lane page: the dataLayer +
# Formspree funnel splits on this string exactly; a page shipping the wrong
# slug (typo, or copy-paste from a sibling) collapses two lanes into one in
# every downstream funnel view. The contract per page:
#   1. >= MIN_LANE_CTAS on-page `data-intent="service:*|portfolio:*"` CTAs,
#      every intent present in INTENT_TO_TYPE (else big7.js prefill no-ops).
#   2. A hidden `<input name="source" value="<slug>">` whose default equals
#      this map's slug — the Formspree lane-attribution replacement for the
#      old per-deep-link `src=` param.
REBUILT_LANE_SRC: dict[str, str] = {
    "commercial-industrial.html": "commercial-industrial-page",
    "residential-construction.html": "residential-page",
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
            # count=0 (all occurrences): the combined surface carries the map
            # twice (index legacy shim `var` copy + big7.js `const` copy) —
            # deleting only the first would leave the parsed big7.js map intact
            # and the mutation would be a no-op against check().
            re.sub(
                rf"""['"]{re.escape(a_intent)}['"]\s*:\s*['"][^'"]+['"]\s*,?""",
                "",
                html,
                count=0,
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

    total = len(cases) + len(rebuilt_cases)
    print(
        f"SELFTEST OK: {total} broken inputs all caught with the expected error "
        f"({len(cases)} mapping/attribution + {len(rebuilt_cases)} rebuilt-lane)."
    )
    return 0


def main(argv: list[str]) -> int:
    surfaces = [INDEX, BIG7_JS] + [REPO_ROOT / lane for lane in LANE_PAGES]
    for path in surfaces:
        if not path.exists():
            print(f"FAIL: {path} not found", file=sys.stderr)
            return 1

    html = "\n".join(path.read_text(encoding="utf-8") for path in surfaces)

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
        errors.extend(check_rebuilt_lane(
            mapping, lane_html, lane,
            expected_src=REBUILT_LANE_SRC[lane],
            min_ctas=MIN_LANE_CTAS,
        ))
        lane_link_count += len(parse_intents(lane_html))

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(
        f"OK: {len(mapping)} INTENT_TO_TYPE entries, {len(intents)} CTA intents, "
        f"{len(radios)} projectType radios — contract holds; attribution loop wired. "
        f"{lane_link_count} lane CTA(s) across {len(LANE_PAGES)} destination page(s), "
        f"each carrying on-page data-intent CTAs + its hidden source slug "
        f"(floor {MIN_LANE_CTAS} CTAs per lane)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
