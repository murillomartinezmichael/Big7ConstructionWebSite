"""
Intake analytics payload contract test (tick 19).

Why: `test_conversion.py` locks the *presence* of `track('cta_click'` and
`track('intake_submit'` substrings, and `test_primary_ctas.py` locks that
`cta_click` derives `position` and puts it in the payload. Nothing today locks
the *rest* of the payload keys the funnel analytics depends on.

CONVERSION_STANDARDS.md § 4 declares these required fields:

| Stage         | Event           | Required fields                                 |
|---------------|-----------------|--------------------------------------------------|
| CTA clicked   | `cta_click`     | intent, page, position                          |
| Intake started| `intake_start`  | intent, page                                    |
| Intake sent   | `intake_submit` | intent, has_prefill (bool), message_length      |

A silent regression that drops `has_prefill` (or renames it to `prefill`, or
inlines it as `true` because "we always prefill anyway") kills the funnel view
that measures whether prefilled intakes convert better than blank ones. No
existing test catches that class of drift.

Contract (all must hold on index.html):
  1. Exactly one `track('cta_click'` call site — a duplicate is a fan-out bug
     where the same click double-fires and every funnel number doubles.
  2. That `cta_click` payload literal declares keys: `intent`, `page`,
     `position`, `label`. Extra keys allowed (spec floors the required set).
  3. Exactly one `track('intake_submit'` call site.
  4. That `intake_submit` payload literal declares keys: `intent`,
     `has_prefill`, `message_length`.
  5. `has_prefill` is derived from `PREFILL_MARK` (not hardcoded `true`/`false`
     and not derived from some other heuristic that silently drifts from the
     actual prefill marker).
  6. `message_length` is derived from `.trim().length` (guards against a
     refactor that ships `.length` — whitespace-only messages count as 0
     length, but plain `.length` on a whitespace-only textarea returns >0).
  7. The submit-event listener is wired with `capture=true` (third arg
     `true`). Without it, a `preventDefault()` in an earlier handler skips
     the analytics event before Formspree fetch fires — silent attribution
     drop.
  8. Exactly one `track('intake_start'` call site. Without this event the
     funnel has a hidden hole between `cta_click` and `intake_submit`:
     "clicked but bailed on the form" is indistinguishable from "never
     touched the form" and every conversion-rate delta is off by that gap.
  9. That `intake_start` payload literal declares keys: `intent`, `page`
     (CONVERSION_STANDARDS.md § 4 minimum). Extra keys allowed.
 10. `intake_start` is wired via `focusin` on the form (not `focus` — `focus`
     does not bubble and would miss the vast majority of first-touch events
     since it fires on the field, not the form). A per-page-view guard
     (`intakeStarted` boolean in the closure) must exist so a user tabbing
     across every field does not re-fire the event dozens of times and
     corrupt the funnel numerator.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "index.html"

# `track('event_name', { ... })` — payload literal ends at the matching `}`.
# Capture the raw payload substring so we can walk key names off it. We deliberately
# match only one level of braces; the payloads under test are all flat.
CTA_CLICK_RE = re.compile(
    r"track\(\s*'cta_click'\s*,\s*\{(?P<body>[^}]*)\}\s*\)",
    re.DOTALL,
)
INTAKE_SUBMIT_RE = re.compile(
    r"track\(\s*'intake_submit'\s*,\s*\{(?P<body>[^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\s*\)",
    re.DOTALL,
)
INTAKE_START_RE = re.compile(
    r"track\(\s*'intake_start'\s*,\s*\{(?P<body>[^}]*)\}\s*\)",
    re.DOTALL,
)
# Key names in an object literal: `foo:` at start of tokenish position.
PAYLOAD_KEY_RE = re.compile(r"(?:^|[,{\s])(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:")

CTA_CLICK_REQUIRED = {"intent", "page", "position", "label"}
INTAKE_SUBMIT_REQUIRED = {"intent", "has_prefill", "message_length"}
INTAKE_START_REQUIRED = {"intent", "page"}

# Submit listener must be wired in capture phase. Without it, a preventDefault
# in a nested handler skips analytics silently.
SUBMIT_LISTENER_CAPTURE_RE = re.compile(
    r"form\.addEventListener\(\s*'submit'\s*,\s*function\s*\([^)]*\)\s*\{",
    re.DOTALL,
)

# Intake-start must attach to the form via `focusin` (which bubbles) —
# `focus` (which does not bubble) would only fire when the form itself
# receives focus, which never happens in practice.
FOCUSIN_LISTENER_RE = re.compile(
    r"form\.addEventListener\(\s*'focusin'\s*,",
    re.DOTALL,
)
# Guard flag must live in the closure so the event fires at most once per
# page view — otherwise every tab-jump across the ~9-field form re-fires it.
INTAKE_START_GUARD_RE = re.compile(
    r"\blet\s+intakeStarted\s*=\s*false\b",
)


def _payload_keys(body: str) -> set[str]:
    return {m.group("key") for m in PAYLOAD_KEY_RE.finditer(body)}


def check(html: str) -> list[str]:  # noqa: C901 - single flat contract by design
    errors: list[str] = []

    # (1) exactly one cta_click site
    cta_matches = list(CTA_CLICK_RE.finditer(html))
    if len(cta_matches) != 1:
        errors.append(
            f"expected exactly 1 `track('cta_click', {{...}})` call, found {len(cta_matches)} "
            f"— a duplicate call double-fires and doubles every funnel number"
        )
    # (2) cta_click payload keys
    if cta_matches:
        keys = _payload_keys(cta_matches[0].group("body"))
        missing = CTA_CLICK_REQUIRED - keys
        if missing:
            errors.append(
                f"cta_click payload missing required key(s) {sorted(missing)} "
                f"(payload had {sorted(keys)}); CONVERSION_STANDARDS.md § 4 requires "
                f"{sorted(CTA_CLICK_REQUIRED)}"
            )

    # (3) exactly one intake_submit site
    intake_matches = list(INTAKE_SUBMIT_RE.finditer(html))
    if len(intake_matches) != 1:
        errors.append(
            f"expected exactly 1 `track('intake_submit', {{...}})` call, found {len(intake_matches)}"
        )
    # (4) intake_submit payload keys
    intake_body = ""
    if intake_matches:
        intake_body = intake_matches[0].group("body")
        keys = _payload_keys(intake_body)
        missing = INTAKE_SUBMIT_REQUIRED - keys
        if missing:
            errors.append(
                f"intake_submit payload missing required key(s) {sorted(missing)} "
                f"(payload had {sorted(keys)}); CONVERSION_STANDARDS.md § 4 requires "
                f"{sorted(INTAKE_SUBMIT_REQUIRED)}"
            )

        # (5) has_prefill must be derived from PREFILL_MARK
        # The value expression sits between `has_prefill:` and the next `,` (or `}`).
        hp_match = re.search(
            r"has_prefill\s*:\s*(?P<expr>[^,}\n]+)",
            intake_body,
        )
        if hp_match and "PREFILL_MARK" not in hp_match.group("expr"):
            errors.append(
                f"has_prefill value {hp_match.group('expr').strip()!r} is not derived from "
                f"PREFILL_MARK — funnel would count blank+typed intakes as prefilled or vice versa"
            )

        # (6) message_length must use .trim().length
        ml_match = re.search(
            r"message_length\s*:\s*(?P<expr>[^,}\n]+)",
            intake_body,
        )
        if ml_match and ".trim().length" not in ml_match.group("expr"):
            errors.append(
                f"message_length value {ml_match.group('expr').strip()!r} does not use "
                f".trim().length — a whitespace-only textarea would report >0 length and "
                f"pollute the funnel"
            )

    # (7) submit listener wired with capture=true
    listener_matches = list(SUBMIT_LISTENER_CAPTURE_RE.finditer(html))
    if not listener_matches:
        errors.append(
            "no `form.addEventListener('submit', function(...) { ... })` — intake_submit "
            "will not fire on the form send"
        )
    else:
        # Walk forward from the *last* submit listener open to its matching `}` and check
        # that the addEventListener call ends with `, true)`.
        m = listener_matches[-1]
        depth = 0
        end = -1
        for i in range(m.end() - 1, len(html)):
            c = html[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end < 0:
            errors.append("submit listener body did not close — malformed IIFE")
        else:
            tail = html[end : end + 40]
            if not re.search(r"\}\s*,\s*true\s*\)", tail):
                errors.append(
                    "submit listener is not registered with capture=true — a nested "
                    "preventDefault() will skip the intake_submit event"
                )

    # (8) exactly one intake_start site
    start_matches = list(INTAKE_START_RE.finditer(html))
    if len(start_matches) != 1:
        errors.append(
            f"expected exactly 1 `track('intake_start', {{...}})` call, found {len(start_matches)} "
            f"— duplicates double the funnel numerator; zero leaves a hidden hole between "
            f"cta_click and intake_submit"
        )
    # (9) intake_start payload keys
    if start_matches:
        keys = _payload_keys(start_matches[0].group("body"))
        missing = INTAKE_START_REQUIRED - keys
        if missing:
            errors.append(
                f"intake_start payload missing required key(s) {sorted(missing)} "
                f"(payload had {sorted(keys)}); CONVERSION_STANDARDS.md § 4 requires "
                f"{sorted(INTAKE_START_REQUIRED)}"
            )

    # (10) intake_start wired via `focusin` on the form (not `focus`)
    if not FOCUSIN_LISTENER_RE.search(html):
        errors.append(
            "intake_start must attach via `form.addEventListener('focusin', ...)` — `focus` "
            "does not bubble, so a listener on the form element would never fire when the "
            "user focuses a nested field"
        )
    # (10b) guard flag must exist so the event fires at most once per page view
    if not INTAKE_START_GUARD_RE.search(html):
        errors.append(
            "intake_start needs a `let intakeStarted = false` guard in the closure — without "
            "it, every tab-jump across the ~9-field form re-fires intake_start and inflates "
            "the funnel numerator"
        )

    return errors


def _baseline_html() -> str:
    """Synthetic minimal HTML mirroring the real analytics shape."""
    return """<html><body>
<form class="cform"><textarea name="message"></textarea><button>Send</button></form>
<script>
  const PREFILL_MARK = '\\u2500 Big 7 brief \\u2500\\n';
  function track(name, payload) { (window.dataLayer = window.dataLayer || []).push({event: name, ...payload}); }
  document.addEventListener('click', function (e) {
    const el = e.target.closest('[data-intent]');
    if (!el) return;
    const intent = el.getAttribute('data-intent');
    const position = (intent.split(':')[1] || 'unspecified');
    const label = el.textContent.trim();
    track('cta_click', { intent: intent, page: 'home', position: position, label: label });
  });
  const form = document.querySelector('form.cform');
  if (form) {
    let intakeStarted = false;
    form.addEventListener('focusin', function () {
      if (intakeStarted) return;
      intakeStarted = true;
      const checked = document.querySelector('input[name="projectType"]:checked');
      track('intake_start', {
        intent: checked ? 'type:' + checked.value : 'type:unset',
        page: 'home'
      });
    }, true);
    form.addEventListener('submit', function () {
      const checked = document.querySelector('input[name="projectType"]:checked');
      const ta = form.querySelector('textarea[name="message"]');
      track('intake_submit', {
        intent: checked ? 'type:' + checked.value : 'type:unset',
        has_prefill: !!(ta && ta.value.indexOf(PREFILL_MARK) === 0),
        message_length: ta ? ta.value.trim().length : 0
      });
    }, true);
  }
</script>
</body></html>
"""


def _selftest(_live_html: str) -> int:
    baseline = _baseline_html()
    baseline_errors = check(baseline)
    if baseline_errors:
        print("SELFTEST ABORT: synthetic baseline fails check() — fix the fixture first:", file=sys.stderr)
        for e in baseline_errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    cases: list[tuple[str, str, str]] = [
        (
            "cta_click.label field dropped",
            baseline.replace(", label: label ", " "),
            "cta_click payload missing required key(s) ['label']",
        ),
        (
            "cta_click.page field dropped",
            baseline.replace("page: 'home', ", ""),
            "cta_click payload missing required key(s) ['page']",
        ),
        (
            "intake_submit.has_prefill field dropped",
            re.sub(r"has_prefill:[^,]+,\s*", "", baseline),
            "intake_submit payload missing required key(s) ['has_prefill']",
        ),
        (
            "intake_submit.message_length field dropped",
            re.sub(r"message_length:[^\n]+\n", "\n", baseline),
            "intake_submit payload missing required key(s) ['message_length']",
        ),
        (
            "has_prefill hardcoded to true (loses signal)",
            baseline.replace(
                "has_prefill: !!(ta && ta.value.indexOf(PREFILL_MARK) === 0),",
                "has_prefill: true,",
            ),
            "not derived from PREFILL_MARK",
        ),
        (
            "message_length drops .trim() (whitespace pollutes)",
            baseline.replace(
                "message_length: ta ? ta.value.trim().length : 0",
                "message_length: ta ? ta.value.length : 0",
            ),
            "does not use .trim().length",
        ),
        (
            "submit listener capture=true removed",
            baseline.replace("}, true);", "});"),
            "capture=true",
        ),
        (
            "cta_click site duplicated (double-fire)",
            baseline.replace(
                "track('cta_click', { intent: intent, page: 'home', position: position, label: label });",
                "track('cta_click', { intent: intent, page: 'home', position: position, label: label });\n"
                "    track('cta_click', { intent: intent, page: 'home', position: position, label: label });",
            ),
            "found 2",
        ),
        (
            "intake_submit call removed entirely",
            re.sub(r"track\('intake_submit'[^)]+\)[^;]*;", "", baseline, flags=re.DOTALL),
            "found 0",
        ),
        (
            "intake_start call removed entirely (funnel hole)",
            re.sub(r"track\('intake_start'[^)]+\)[^;]*;", "", baseline, flags=re.DOTALL),
            "expected exactly 1 `track('intake_start'",
        ),
        (
            "intake_start.page dropped",
            baseline.replace("page: 'home'\n", "\n"),
            "intake_start payload missing required key(s) ['page']",
        ),
        (
            "intake_start listener uses `focus` (non-bubbling) instead of `focusin`",
            baseline.replace("'focusin'", "'focus'"),
            "must attach via `form.addEventListener('focusin'",
        ),
        (
            "intake_start guard removed (event re-fires on every field tab-jump)",
            baseline.replace("let intakeStarted = false;\n    ", ""),
            "`let intakeStarted = false` guard",
        ),
    ]

    failures: list[str] = []
    for label, mutated, needle in cases:
        if mutated == baseline:
            failures.append(f"{label}: mutation was a no-op (replace did not match)")
            continue
        errs = check(mutated)
        if not errs:
            failures.append(f"{label}: mutation slipped through — check() returned no errors")
            continue
        if not any(needle in e for e in errs):
            failures.append(
                f"{label}: mutation was caught but no error contained {needle!r}. Got: {errs}"
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

    errors = check(html)
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(
        f"OK: intake analytics payload contract holds — cta_click carries "
        f"{sorted(CTA_CLICK_REQUIRED)}, intake_start carries "
        f"{sorted(INTAKE_START_REQUIRED)} (focusin + intakeStarted guard), "
        f"intake_submit carries {sorted(INTAKE_SUBMIT_REQUIRED)}, "
        f"has_prefill derived from PREFILL_MARK, message_length uses .trim().length, "
        f"submit listener registered with capture=true."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
