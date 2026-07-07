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
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "index.html"

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
        errors.append("could not find `const INTENT_TO_TYPE = { ... }` block in index.html")
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
            errors.append(f"index.html is missing required attribution substring: {needle!r}")

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

    print(f"SELFTEST OK: {len(cases)} broken inputs all caught with the expected error.")
    return 0


def main(argv: list[str]) -> int:
    if not INDEX.exists():
        print(f"FAIL: {INDEX} not found", file=sys.stderr)
        return 1

    html = INDEX.read_text(encoding="utf-8")

    if "--selftest" in argv:
        return _selftest(html)

    errors, mapping, radios, intents = check(html)

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(
        f"OK: {len(mapping)} INTENT_TO_TYPE entries, {len(intents)} CTA intents, "
        f"{len(radios)} projectType radios — contract holds; attribution loop wired."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
