"""
Intake form structural contract test.

Why: the two lane destination pages each carry a hand-rolled intake form —
the money-path surfaces where every CTA ends (2026-07-17 two-path
restructure; index.html is a chooser and MUST NOT carry a form). `test_conversion.py` locks the CTA
`data-intent` -> `INTENT_TO_TYPE` -> `projectType` radio wiring, but says
nothing about the form *itself*: whether the Formspree endpoint drifted to a
dev URL, whether the required fields the ../../docs/CONVERSION_STANDARDS.md
lists (name / phone / project-type) still carry `required`, whether the
honeypot survived a careless refactor, or whether the alt-call `tel:` link
still points at the same number as the JSON-LD `telephone`.

Each of those is a silent-death class:
  - Wrong Formspree action -> intakes 200 in the browser, land nowhere.
  - `required` stripped off `phone` -> visitor submits without a callable
    number, quote intake goes to email-only and 30-40% never convert.
  - Honeypot removed -> Formspree quota burns on spam within a week.
  - `tel:` and JSON-LD phone drift -> Google shows one number, the page's
    "or call" link opens another; caller confusion + phantom missed calls.

Contract (all must hold, per lane page):
  0. index.html carries NO `<form class="cform">` (chooser lock).
  1. Exactly one `<form class="cform" ...>` exists per lane page.
  2. `action` is a `formspree.io/f/<hash>` URL over https.
  3. `method="POST"`.
  4. `onsubmit="submitForm(event)"` handler is wired.
  5. Required inputs — `name` (text) / `email` (email) / `phone` (tel) — each
     carries `required` + correct `type` + a sensible `autocomplete` value.
  6. `projectType` radios exist, count >= MIN_RADIOS, and at least one radio
     carries `required` (browsers enforce required-of-group on the first).
  7. Honeypot: an input with `name="website"` is present, hidden from a11y
     (either wrapped in `display:none` OR `aria-hidden="true"`), and carries
     `tabindex="-1"` + `autocomplete="off"` so keyboard/password managers
     do not fill it and human visitors cannot see or reach it.
  8. Formspree control fields: `_subject` (hidden, value carries the lane's
     subject line) and `_replyto` (hidden — set by the email `oninput`);
     hidden `source` input whose default equals the lane's attribution slug.
  9. Alt-call `<a href="tel:...">` sits inside the form's submit block.
 10. Phone agreement: the `tel:` digits and JSON-LD `telephone` digits, both
     stripped of non-digit chars, must have matching *last 10 digits*. This
     is robust to `+1-` prefix / punctuation differences but catches a real
     phone-number drift between the two surfaces.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "index.html"

# Per-lane form contract (2026-07-17 two-path restructure): exact radio value
# set, lane subject needle, and hidden-source attribution slug.
FORM_PAGES: dict[str, dict] = {
    "commercial-industrial.html": {
        "radios": {"commercial-new", "industrial-warehouse", "tenant-improvement"},
        "subject": "New commercial bid",
        "source": "commercial-industrial-page",
        # Commercial-scale budget ranges (2026-07-17, Mike's ask: the two
        # lanes must NOT share pricing ranges — a homeowner staring at
        # "$5M-$25M" chips bounces, a facilities director staring at
        # "<$50K" chips doubts the shop's capacity).
        "budgets": {"lt-500k", "500k-1m", "1m-5m", "5m-25m", "25m-plus", "tbd"},
    },
    "residential-construction.html": {
        "radios": {"residential-custom", "residential-remodel", "trades-only"},
        "subject": "New residential bid",
        "source": "residential-page",
        # Homeowner-scale budget ranges — see note above.
        "budgets": {"lt-50k", "50k-150k", "150k-500k", "500k-1m", "1m-plus", "tbd"},
    },
}
MIN_RADIOS = 3  # per-lane floor; the exact value-set check below is the real lock.

FORM_OPEN_RE = re.compile(
    r'<form\b[^>]*\bclass="cform"[^>]*>',
    re.IGNORECASE,
)
# Attribute regex handles both quoted values (`name="value"`) AND bare boolean
# attributes (`required`, `disabled`, `checked`). Boolean attributes end up in
# the returned dict with value `""` — presence check via `"required" in attrs`.
ATTR_RE = re.compile(r'(?P<name>[a-zA-Z_:][\w:.\-]*)(?:\s*=\s*"(?P<val>[^"]*)")?')
TAG_PREFIX_RE = re.compile(r'^<[a-zA-Z][\w\-]*\s*')
TAG_SUFFIX_RE = re.compile(r'/?>$')
INPUT_TAG_RE = re.compile(r'<input\b[^>]*/?>', re.IGNORECASE)
ANCHOR_TAG_RE = re.compile(r'<a\b[^>]*>', re.IGNORECASE)
JSONLD_RE = re.compile(
    r'<script\s+type="application/ld\+json"\s*>(?P<body>.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def _attrs(tag: str) -> dict[str, str]:
    # Strip `<tagname` prefix and `>` (or `/>`) suffix so the tag name itself
    # is not parsed as a boolean attribute.
    inner = TAG_PREFIX_RE.sub("", tag, count=1)
    inner = TAG_SUFFIX_RE.sub("", inner, count=1)
    out: dict[str, str] = {}
    for m in ATTR_RE.finditer(inner):
        val = m.group("val")
        out[m.group("name").lower()] = val if val is not None else ""
    return out


def _find_form(html: str) -> tuple[str | None, str]:
    """Return (form_inner_html, err). Slice from `<form ... class="cform" ...>` to
    the next `</form>`. The form is the only one on the page — a drift adding a
    second cform (say a duplicated section) also gets caught here."""
    matches = list(FORM_OPEN_RE.finditer(html))
    if not matches:
        return None, 'no `<form class="cform" ...>` found'
    if len(matches) > 1:
        return None, f'expected 1 `<form class="cform">`, found {len(matches)}'
    start = matches[0].start()
    close = html.find("</form>", matches[0].end())
    if close == -1:
        return None, 'form opens but never closes (`</form>` not found)'
    return html[start : close + len("</form>")], ""


def _inputs_by_name(form_html: str) -> dict[str, list[dict[str, str]]]:
    """Group every `<input>` tag on the form by `name` attribute."""
    out: dict[str, list[dict[str, str]]] = {}
    for m in INPUT_TAG_RE.finditer(form_html):
        attrs = _attrs(m.group(0))
        name = attrs.get("name")
        if not name:
            continue
        out.setdefault(name, []).append(attrs)
    return out


def _digits(s: str) -> str:
    return re.sub(r"\D+", "", s)


def _jsonld_telephone(html: str) -> tuple[str | None, str]:
    """Pull `telephone` from the first LocalBusiness-shaped JSON-LD block."""
    for m in JSONLD_RE.finditer(html):
        try:
            block = json.loads(m.group("body"))
        except json.JSONDecodeError:
            continue
        tel = block.get("telephone")
        if not (isinstance(tel, str) and tel.strip()):
            provider = block.get("provider")
            if isinstance(provider, dict):
                tel = provider.get("telephone")
        if isinstance(tel, str) and tel.strip():
            return tel, ""
    return None, "no JSON-LD block with a `telephone` field found"


def check(
    html: str,
    radios_expected: set[str] | None = None,
    subject_needle: str = "",
    source_expected: str = "",
    budgets_expected: set[str] | None = None,
) -> list[str]:  # noqa: C901 - single flat contract check by design
    errors: list[str] = []

    form_html, form_err = _find_form(html)
    if form_err:
        errors.append(form_err)
        return errors
    assert form_html is not None

    # (1) form open-tag attributes: action, method, onsubmit.
    form_open = FORM_OPEN_RE.search(form_html).group(0)  # type: ignore[union-attr]
    form_attrs = _attrs(form_open)

    action = form_attrs.get("action", "")
    if not re.fullmatch(r"https://formspree\.io/f/[A-Za-z0-9]+", action):
        errors.append(
            f'form action={action!r} does not match https://formspree.io/f/<id> '
            f"— endpoint drifted or was replaced (silent intake-drop risk)"
        )

    method = form_attrs.get("method", "").upper()
    if method != "POST":
        errors.append(f'form method={method!r} — must be "POST" for Formspree')

    if "submitForm" not in form_attrs.get("onsubmit", ""):
        errors.append(
            'form onsubmit handler is missing `submitForm(...)` — the fetch-based '
            "submit that keeps the visitor on-page will not run"
        )

    inputs = _inputs_by_name(form_html)

    # (2) required inputs — name / email / phone — with correct type + autocomplete.
    required_spec = {
        "name":  {"type": "text",  "autocomplete": "name"},
        "email": {"type": "email", "autocomplete": "email"},
        "phone": {"type": "tel",   "autocomplete": "tel"},
    }
    for fname, spec in required_spec.items():
        tags = inputs.get(fname, [])
        if not tags:
            errors.append(f'required input name="{fname}" is missing from the form')
            continue
        tag = tags[0]
        if tag.get("type", "").lower() != spec["type"]:
            errors.append(
                f'input name="{fname}" has type={tag.get("type")!r}, expected {spec["type"]!r}'
            )
        if "required" not in tag:
            errors.append(
                f'input name="{fname}" is missing the `required` attribute — '
                f"browser will accept blank submissions"
            )
        ac = tag.get("autocomplete", "").lower()
        if ac != spec["autocomplete"]:
            errors.append(
                f'input name="{fname}" has autocomplete={ac!r}, expected {spec["autocomplete"]!r} '
                f"(password managers + mobile keyboards rely on this)"
            )

    # (3) projectType radios — count above floor, first one carries `required`.
    radios = inputs.get("projectType", [])
    radio_vals = {r.get("value", "") for r in radios if r.get("type", "").lower() == "radio"}
    radio_count = len(radio_vals)
    if radio_count < MIN_RADIOS:
        errors.append(
            f"projectType radios: found {radio_count}, floor is {MIN_RADIOS} "
            f"(a stealth collapse of options below this floor is a scope-drop signal)"
        )
    elif radios_expected is not None and radio_vals != radios_expected:
        errors.append(
            f"projectType radio values {sorted(radio_vals)} do not match the lane's "
            f"expected set {sorted(radios_expected)} — a wrong-lane paste or a "
            f"renamed value silently breaks big7.js prefill + funnel bucketing"
        )
    elif not any("required" in r for r in radios):
        errors.append(
            "no projectType radio carries `required` — browsers only enforce required "
            "on radio groups if at least one member declares it; visitors can submit "
            "without picking a project type"
        )

    # (3b) budget chips: the lane's exact value set. The two lanes carry
    # DIFFERENT ranges by design (commercial-scale vs homeowner-scale) — a
    # copy-paste that re-unifies them ships unrealistic pricing to one
    # audience and this catches it.
    if budgets_expected is not None:
        budget_vals = {
            b.get("value", "")
            for b in inputs.get("budget", [])
            if b.get("type", "").lower() == "radio"
        }
        if budget_vals != budgets_expected:
            errors.append(
                f"budget chip values {sorted(budget_vals)} do not match the lane's "
                f"expected set {sorted(budgets_expected)} — the two lanes must not "
                f"share pricing ranges (commercial-scale vs homeowner-scale)"
            )

    # (4) Honeypot: name="website", hidden + tabindex + autocomplete=off.
    honeypots = inputs.get("website", [])
    if not honeypots:
        errors.append(
            'honeypot input name="website" is missing — Formspree quota will burn on spam'
        )
    else:
        hp = honeypots[0]
        # Container hidden either by `style="display:none"` on a wrapping div OR by
        # `aria-hidden="true"` on that wrapper. Walk backwards from the honeypot tag
        # in the form HTML to find the nearest opening `<div ...>` wrapper.
        hp_pos = form_html.find(f'name="website"')
        preceding = form_html[:hp_pos]
        wrap_match = None
        for m in re.finditer(r'<div\b[^>]*>', preceding, re.IGNORECASE):
            wrap_match = m
        wrap_attrs = _attrs(wrap_match.group(0)) if wrap_match else {}
        style = wrap_attrs.get("style", "").lower().replace(" ", "")
        hidden_by_style = "display:none" in style
        hidden_by_aria = wrap_attrs.get("aria-hidden", "").lower() == "true"
        if not (hidden_by_style or hidden_by_aria):
            errors.append(
                'honeypot wrapper is not hidden (needs `style="display:none"` OR '
                '`aria-hidden="true"`) — real visitors will see + fill the field'
            )
        if hp.get("tabindex") != "-1":
            errors.append(
                'honeypot input is missing `tabindex="-1"` — keyboard visitors can '
                "tab into it"
            )
        if hp.get("autocomplete", "").lower() != "off":
            errors.append(
                'honeypot input is missing `autocomplete="off"` — password managers '
                "will helpfully fill it and every autofilled intake gets marked spam"
            )

    # (5) Formspree control fields.
    for hidden_name in ("_subject", "_replyto"):
        tags = inputs.get(hidden_name, [])
        if not tags:
            errors.append(f'missing hidden Formspree control input name="{hidden_name}"')
            continue
        if tags[0].get("type", "").lower() != "hidden":
            errors.append(
                f'input name="{hidden_name}" must be type="hidden" '
                f"(got {tags[0].get('type')!r})"
            )
    subj = inputs.get("_subject", [{}])[0].get("value", "")
    if inputs.get("_subject") and not subj.strip():
        errors.append('hidden `_subject` input has empty value — Formspree emails will lack a subject line')
    elif inputs.get("_subject") and subject_needle and subject_needle not in subj:
        errors.append(
            f"hidden `_subject` value {subj!r} does not contain the lane's expected "
            f"subject needle {subject_needle!r} — intakes from the two lanes become "
            f"indistinguishable in the estimator's inbox"
        )

    # Hidden lane-attribution `source` input with the lane's default slug.
    sources = inputs.get("source", [])
    if not sources:
        errors.append('missing hidden lane-attribution input name="source"')
    else:
        stag = sources[0]
        if stag.get("type", "").lower() != "hidden":
            errors.append(f'input name="source" must be type="hidden" (got {stag.get("type")!r})')
        sval = stag.get("value", "")
        if source_expected and sval != source_expected:
            errors.append(
                f'hidden `source` default {sval!r} does not match the lane slug '
                f"{source_expected!r} — every intake from this page mislabels its lane "
                f"in the funnel"
            )

    # (6) alt-call tel: link sits inside the submit block.
    tel_hrefs: list[str] = []
    for m in ANCHOR_TAG_RE.finditer(form_html):
        href = _attrs(m.group(0)).get("href", "")
        if href.lower().startswith("tel:"):
            tel_hrefs.append(href)
    if not tel_hrefs:
        errors.append(
            "no `<a href=\"tel:...\">` alt-call link inside the form — the 'or call' "
            "fallback for visitors who won't fill the form is gone"
        )

    # (7) tel: <-> JSON-LD phone agreement (last 10 digits).
    jsonld_tel, tel_err = _jsonld_telephone(html)
    if tel_err:
        errors.append(tel_err)
    elif tel_hrefs and jsonld_tel:
        form_last10 = _digits(tel_hrefs[0])[-10:]
        jsonld_last10 = _digits(jsonld_tel)[-10:]
        if len(form_last10) < 10 or len(jsonld_last10) < 10:
            errors.append(
                f"one of tel:={tel_hrefs[0]!r} / JSON-LD telephone={jsonld_tel!r} "
                f"has fewer than 10 digits — cannot verify agreement"
            )
        elif form_last10 != jsonld_last10:
            errors.append(
                f"phone number drift: tel: link last-10 digits = {form_last10!r}, "
                f"JSON-LD telephone last-10 digits = {jsonld_last10!r} "
                f"(Google shows one number, the page dials another)"
            )

    return errors


def _minimal_valid_form_html() -> str:
    """Synthetic-but-realistic baseline used for `--selftest`. Must PASS `check()`.

    Kept close to the shape of the real form (Formspree action, three required
    contact fields, `MIN_RADIOS` project-type radios with `required` on the first,
    honeypot in a `display:none` wrapper, hidden Formspree controls, alt-call
    tel link, JSON-LD block with a matching telephone) so mutations exercise the
    same code paths the real HTML does.
    """
    radios = "\n".join(
        f'<label><input type="radio" name="projectType" value="r{i}"'
        + (' required' if i == 0 else "")
        + '/></label>'
        for i in range(MIN_RADIOS)
    )
    return f"""
<html><head>
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"GeneralContractor","name":"X","telephone":"+1-555-700-0007"}}
</script>
</head><body>
<form class="cform" action="https://formspree.io/f/abcdef123" method="POST" onsubmit="submitForm(event)">
  <input type="hidden" name="_subject" value="New bid request"/>
  <input type="hidden" name="_replyto" value=""/>
  <input type="hidden" name="source" value="lane-selftest-page"/>
  <label><input type="radio" name="budget" value="b0"/></label>
  <label><input type="radio" name="budget" value="b1"/></label>
  <input type="text"  name="name"  required autocomplete="name"/>
  <input type="email" name="email" required autocomplete="email"/>
  <input type="tel"   name="phone" required autocomplete="tel"/>
  {radios}
  <div style="display:none" aria-hidden="true">
    <input type="text" name="website" tabindex="-1" autocomplete="off"/>
  </div>
  <button type="submit">Send</button>
  <a href="tel:5557000007">or call (555) 700-0007</a>
</form>
</body></html>
"""


def _selftest(_live_html: str) -> int:
    """Mutate a synthetic-but-realistic baseline N known-broken ways.

    Each case names the error substring that MUST appear — a mutation that
    causes some other error to fire, or none at all, is a regression in the
    test itself (a rubber-stamp check is worse than no check).
    """
    fixture_spec = dict(
        radios_expected={f"r{i}" for i in range(MIN_RADIOS)},
        subject_needle="New bid request",
        source_expected="lane-selftest-page",
        budgets_expected={"b0", "b1"},
    )
    baseline = _minimal_valid_form_html()
    baseline_errors = check(baseline, **fixture_spec)
    if baseline_errors:
        print("SELFTEST ABORT: synthetic baseline fails check() — fix the fixture first:", file=sys.stderr)
        for e in baseline_errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    cases: list[tuple[str, str, str]] = [
        (
            "formspree action drifted to a dev URL",
            baseline.replace(
                'action="https://formspree.io/f/abcdef123"',
                'action="https://dev.example.com/intake"',
            ),
            "does not match https://formspree.io/f",
        ),
        (
            "form method downgraded to GET",
            baseline.replace('method="POST"', 'method="GET"'),
            "must be \"POST\"",
        ),
        (
            "onsubmit handler stripped",
            baseline.replace('onsubmit="submitForm(event)"', ""),
            "missing `submitForm",
        ),
        (
            "phone field lost its `required`",
            baseline.replace(
                '<input type="tel"   name="phone" required autocomplete="tel"/>',
                '<input type="tel"   name="phone" autocomplete="tel"/>',
            ),
            'name="phone" is missing the `required`',
        ),
        (
            "email field type downgraded to text",
            baseline.replace(
                '<input type="email" name="email" required autocomplete="email"/>',
                '<input type="text"  name="email" required autocomplete="email"/>',
            ),
            'name="email" has type=\'text\'',
        ),
        (
            "name field autocomplete stripped",
            baseline.replace(
                '<input type="text"  name="name"  required autocomplete="name"/>',
                '<input type="text"  name="name"  required/>',
            ),
            'name="name" has autocomplete=\'\'',
        ),
        (
            "projectType radios collapsed below floor",
            re.sub(
                r'<label><input type="radio" name="projectType" value="r\d+"[^/]*/></label>\n?',
                "",
                baseline,
            ),
            f"floor is {MIN_RADIOS}",
        ),
        (
            "projectType `required` stripped from every radio",
            baseline.replace(' required/>', '/>'),
            "no projectType radio carries `required`",
        ),
        (
            "honeypot removed entirely",
            re.sub(
                r'<div style="display:none"[^>]*>.*?</div>',
                "",
                baseline,
                flags=re.DOTALL,
            ),
            'honeypot input name="website" is missing',
        ),
        (
            "honeypot wrapper no longer hidden",
            baseline.replace(
                '<div style="display:none" aria-hidden="true">',
                '<div>',
            ),
            "honeypot wrapper is not hidden",
        ),
        (
            "honeypot tabindex removed",
            baseline.replace(' tabindex="-1"', ''),
            'missing `tabindex="-1"`',
        ),
        (
            "hidden `_subject` control field deleted",
            baseline.replace(
                '<input type="hidden" name="_subject" value="New bid request"/>',
                '',
            ),
            'missing hidden Formspree control input name="_subject"',
        ),
        (
            "alt-call tel: link removed",
            re.sub(r'<a href="tel:[^"]+">[^<]*</a>', '', baseline),
            'no `<a href="tel:',
        ),
        (
            "tel: link drifted from JSON-LD telephone",
            baseline.replace('href="tel:5557000007"', 'href="tel:4041234567"'),
            "phone number drift",
        ),
        (
            "hidden lane-attribution `source` input deleted",
            baseline.replace(
                '<input type="hidden" name="source" value="lane-selftest-page"/>', ''
            ),
            'missing hidden lane-attribution input name="source"',
        ),
        (
            "hidden `source` drifts to a sibling lane slug (cross-lane paste)",
            baseline.replace('value="lane-selftest-page"', 'value="some-other-page"'),
            "does not match the lane slug",
        ),
        (
            "radio value renamed out of the lane's expected set",
            baseline.replace('value="r1"', 'value="r1-renamed"'),
            "do not match the lane's expected set",
        ),
        (
            "budget chips re-unified with the sibling lane (pricing drift)",
            baseline.replace('name="budget" value="b1"', 'name="budget" value="b1-other-lane"'),
            "must not share pricing ranges",
        ),
    ]

    failures: list[str] = []
    for label, mutated, needle in cases:
        if mutated == baseline:
            failures.append(f"{label}: mutation was a no-op (replace did not match)")
            continue
        errs = check(mutated, **fixture_spec)
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
    if "--selftest" in argv:
        return _selftest("")

    errors: list[str] = []

    # (0) chooser lock: index.html must NOT carry an intake form — the form
    # moved to the lane pages 2026-07-17; a reappearing index form means a
    # revert or a copy-paste re-split of the money surface.
    if not INDEX.exists():
        print(f"FAIL: {INDEX} not found", file=sys.stderr)
        return 1
    if FORM_OPEN_RE.search(INDEX.read_text(encoding="utf-8")):
        errors.append(
            'index.html carries a `<form class="cform">` — the chooser page must '
            "not own an intake form (both lane pages do)"
        )

    for page, spec in FORM_PAGES.items():
        path = REPO_ROOT / page
        if not path.exists():
            errors.append(f"{page}: not found at {path}")
            continue
        html = path.read_text(encoding="utf-8")
        for e in check(
            html,
            radios_expected=spec["radios"],
            subject_needle=spec["subject"],
            source_expected=spec["source"],
            budgets_expected=spec["budgets"],
        ):
            errors.append(f"{page}: {e}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    budget_sets = [frozenset(spec["budgets"]) for spec in FORM_PAGES.values()]
    if len(set(budget_sets)) != len(budget_sets):
        print(
            "FAIL: FORM_PAGES budget specs are identical across lanes — the spec "
            "itself drifted; the lanes must carry different pricing ranges",
            file=sys.stderr,
        )
        return 1

    subjects = {spec["subject"] for spec in FORM_PAGES.values()}
    print(
        f"OK: intake form contract holds on {len(FORM_PAGES)} lane pages — Formspree "
        f"action locked, 3 required contact fields with autocomplete + required, "
        f"per-lane radio value sets + {len(subjects)} distinct subjects + hidden source "
        f"slugs, honeypot hidden + tabindex-off, tel: links agree with JSON-LD "
        f"telephone; index.html carries no form (chooser lock)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
