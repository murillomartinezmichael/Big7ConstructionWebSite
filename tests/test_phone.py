"""
Phone-number single-source contract.

Why: the business phone is the site's primary conversion path — the sticky
mobile call bar, header tel: links, contact blocks, JSON-LD `telephone` +
`contactPoint`, and the big7.js failure copy all carry it. Before this test
the number was hard-coded in ~26 places across 6 shipped files with no lock
that they agree: one hand-edited surface (a new tracking number pasted into
the call bar but not the JSON-LD, say) would ship a site that displays one
number and tells Google another. Now the canonical value lives in ONE place
— `site.config.json` at repo root — and this suite fails the moment any
surface drifts from it.

Second job: the shipped number is still the reserved placeholder
(555) 700-0007 — the call bar dials nothing (PENDING_MANUAL: real number is
client-gated). While `phone.placeholder` is true in the config, the golden
run prints a loud WARN block on every `make test` so no session forgets,
but stays green (the suite must not be red for a known, tracked, Mike-gated
condition). The flag cannot be quietly flipped: `placeholder: false` with a
555 exchange still in the config is a hard FAIL.

Locks:
  1. site.config.json exists, parses, and `phone.digits` is exactly 10
     digits.
  2. Every `tel:` href across the shipped surfaces dials the canonical
     digits.
  3. Every visible `(XXX) XXX-XXXX` display string equals the canonical
     display form.
  4. Every JSON-LD `"telephone"` value equals the canonical `+1-XXX-XXX-XXXX`
     form.
  5. Every known phone-carrying surface has >= 1 canonical occurrence (a
     surface silently losing its number is also drift).
  6. `phone.placeholder: false` while the exchange is still 555 -> FAIL
     (a placeholder cannot be declared real by flipping the flag).
  7. `phone.placeholder: true` -> WARN block on stdout, exit 0.

Python 3.11+ stdlib only (`json`, `re`, `sys`, `pathlib`, `tempfile`).
No pip install, no network.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "site.config.json"

# Every shipped file that carries the phone in any shape. A file listed here
# with ZERO canonical occurrences fails (lock 5). 404.html deliberately not
# listed — it has never carried the number.
SURFACES: tuple[str, ...] = (
    "index.html",
    "commercial-industrial.html",
    "residential-construction.html",
    "south-fulton-distribution.html",
    "accessibility.html",
    "big7.js",
)

TEL_HREF_RE = re.compile(r'href="tel:(?P<num>[^"]*)"', re.IGNORECASE)
DISPLAY_RE = re.compile(r"\(\d{3}\)\s?\d{3}-\d{4}")
JSONLD_TEL_RE = re.compile(r'"telephone"\s*:\s*"(?P<num>[^"]*)"')

# The intake form's <input placeholder="(404) 555-0000"> is an example format
# for the VISITOR's number, not the business line — legitimately different.
# Strip input-placeholder attributes before scanning so they never count.
INPUT_PLACEHOLDER_RE = re.compile(r'placeholder="[^"]*"', re.IGNORECASE)


def load_config(path: Path) -> tuple[dict | None, list[str]]:
    """Parse + validate site.config.json. Returns (config, errors)."""
    errors: list[str] = []
    if not path.is_file():
        return None, [f"{path.name} missing — the phone single-source file is gone"]
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return None, [f"{path.name} is not valid JSON: {e}"]

    phone = cfg.get("phone")
    if not isinstance(phone, dict):
        return None, [f'{path.name}: "phone" must be an object, got {type(phone).__name__}']

    digits = phone.get("digits")
    if not (isinstance(digits, str) and re.fullmatch(r"\d{10}", digits or "")):
        errors.append(
            f'{path.name}: phone.digits must be exactly 10 digits '
            f'(no punctuation), got {digits!r}'
        )
    placeholder = phone.get("placeholder")
    if not isinstance(placeholder, bool):
        errors.append(
            f'{path.name}: phone.placeholder must be true or false, got {placeholder!r}'
        )
    if errors:
        return None, errors

    if placeholder is False and "555" in (digits[:3], digits[3:6]):
        errors.append(
            f'{path.name}: phone.placeholder is false but {digits!r} still uses '
            f'the reserved 555 exchange — a placeholder cannot be declared real '
            f'by flipping the flag; put the client\'s actual number in first'
        )
        return None, errors

    return {"digits": digits, "placeholder": placeholder}, []


def forms(digits: str) -> dict[str, str]:
    """The three shipped shapes derived from the canonical 10 digits."""
    a, b, c = digits[0:3], digits[3:6], digits[6:10]
    return {
        "tel": digits,                 # href="tel:5557000007"
        "display": f"({a}) {b}-{c}",   # (555) 700-0007
        "jsonld": f"+1-{a}-{b}-{c}",   # +1-555-700-0007
    }


def check(files: dict[str, str], digits: str) -> list[str]:
    """files: {surface name: file text}. Returns list of drift errors."""
    f = forms(digits)
    errors: list[str] = []

    for name, text in files.items():
        text = INPUT_PLACEHOLDER_RE.sub("", text)
        occurrences = 0

        for m in TEL_HREF_RE.finditer(text):
            got = re.sub(r"\D", "", m.group("num"))
            if got != digits:
                errors.append(
                    f'{name}: tel: href dials {m.group("num")!r} — canonical is '
                    f'tel:{digits} (site.config.json)'
                )
            else:
                occurrences += 1

        for m in DISPLAY_RE.finditer(text):
            if m.group(0) != f["display"]:
                errors.append(
                    f'{name}: visible number {m.group(0)!r} — canonical display '
                    f'form is {f["display"]!r} (site.config.json)'
                )
            else:
                occurrences += 1

        for m in JSONLD_TEL_RE.finditer(text):
            if m.group("num") != f["jsonld"]:
                errors.append(
                    f'{name}: JSON-LD telephone {m.group("num")!r} — canonical '
                    f'JSON-LD form is {f["jsonld"]!r} (site.config.json)'
                )
            else:
                occurrences += 1

        if occurrences == 0:
            errors.append(
                f'{name}: no canonical phone occurrence found — this surface is '
                f'expected to carry the number (tel: href, display text, or '
                f'JSON-LD); losing it silently is also drift'
            )

    return errors


# ---------------------------------------------------------------------------
# --selftest
# ---------------------------------------------------------------------------

def _valid_files(digits: str = "5557000007") -> dict[str, str]:
    f = forms(digits)
    page = (
        '<html><body>'
        f'<a href="tel:{f["tel"]}" class="nav-phone">{f["display"]}</a>'
        '<script type="application/ld+json">'
        f'{{"@type":"GeneralContractor","telephone":"{f["jsonld"]}"}}'
        '</script>'
        f'<a href="tel:{f["tel"]}" class="cb-call">Call {f["display"]}</a>'
        '</body></html>'
    )
    js = f'if (note) note.textContent = "Email us or call {f["display"]}.";'
    return {"index.html": page, "big7.js": js}


def _selftest() -> None:
    digits = "5557000007"
    baseline = _valid_files(digits)

    errs = check(baseline, digits)
    assert not errs, f"baseline should PASS but got: {errs}"

    # False-positive guard: a form input's example-format placeholder for the
    # VISITOR's phone must not be flagged as business-number drift.
    with_input = {**baseline, "index.html": baseline["index.html"].replace(
        "</body>",
        '<input type="tel" name="phone" placeholder="(404) 555-0000" /></body>')}
    errs = check(with_input, digits)
    assert not errs, f"input-placeholder guard should PASS but got: {errs}"

    mutations: list[tuple[str, dict[str, str], str]] = [
        (
            "tel: href drifts to a different number",
            {**baseline, "index.html": baseline["index.html"].replace(
                'href="tel:5557000007" class="cb-call"',
                'href="tel:5559999999" class="cb-call"')},
            "tel: href dials",
        ),
        (
            "visible display number drifts",
            {**baseline, "big7.js": baseline["big7.js"].replace(
                "(555) 700-0007", "(404) 123-4567")},
            "visible number",
        ),
        (
            "JSON-LD telephone drifts",
            {**baseline, "index.html": baseline["index.html"].replace(
                '"telephone":"+1-555-700-0007"', '"telephone":"+1-555-123-4567"')},
            "JSON-LD telephone",
        ),
        (
            "surface loses its number entirely",
            {**baseline, "big7.js": "console.log('no phone here');"},
            "no canonical phone occurrence",
        ),
    ]
    for label, files, needle in mutations:
        errs = check(files, digits)
        if not errs:
            raise AssertionError(f"mutation {label!r} should FAIL but passed")
        joined = " | ".join(errs)
        if needle not in joined:
            raise AssertionError(
                f"mutation {label!r} raised errors, but none contained {needle!r}: {errs}"
            )

    # Config-level mutations run through load_config against temp files.
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        good = tmp / "good.json"
        good.write_text(json.dumps({"phone": {"digits": digits, "placeholder": True}}))
        cfg, errs = load_config(good)
        assert cfg and not errs, f"valid config should load, got: {errs}"

        config_mutations: list[tuple[str, str, str]] = [
            (
                "digits not 10 digits",
                json.dumps({"phone": {"digits": "555700000", "placeholder": True}}),
                "exactly 10 digits",
            ),
            (
                "placeholder declared real while exchange is still 555",
                json.dumps({"phone": {"digits": digits, "placeholder": False}}),
                "reserved 555 exchange",
            ),
            (
                "config not valid JSON",
                "{not json",
                "not valid JSON",
            ),
            (
                "phone key missing",
                json.dumps({"telephone": digits}),
                '"phone" must be an object',
            ),
        ]
        for label, text, needle in config_mutations:
            p = tmp / "mut.json"
            p.write_text(text)
            cfg, errs = load_config(p)
            if cfg is not None and not errs:
                raise AssertionError(f"config mutation {label!r} should FAIL but passed")
            joined = " | ".join(errs)
            if needle not in joined:
                raise AssertionError(
                    f"config mutation {label!r} raised errors, but none contained "
                    f"{needle!r}: {errs}"
                )

        missing, errs = load_config(tmp / "ghost.json")
        assert missing is None and errs and "missing" in errs[0], \
            f"missing config should FAIL, got: {errs}"

        # False-positive guard: a REAL (non-555) number with placeholder false
        # must load clean.
        real = tmp / "real.json"
        real.write_text(json.dumps({"phone": {"digits": "4047001234", "placeholder": False}}))
        cfg, errs = load_config(real)
        assert cfg and not errs, f"real-number config should PASS, got: {errs}"

    print(
        f"OK: baseline PASS + {len(mutations)} drift mutations + "
        f"{len(config_mutations) + 1} config mutations caught + real-number "
        f"false-positive guard PASS"
    )


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
        return 0

    cfg, errors = load_config(CONFIG_PATH)
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    files: dict[str, str] = {}
    for name in SURFACES:
        path = REPO_ROOT / name
        if not path.is_file():
            print(f"FAIL: expected phone surface {name} missing on disk", file=sys.stderr)
            return 1
        files[name] = path.read_text(encoding="utf-8")

    errors = check(files, cfg["digits"])
    if errors:
        print("FAIL: phone-number drift from site.config.json:", file=sys.stderr)
        for e in errors:
            print("  -", e, file=sys.stderr)
        return 1

    total = sum(
        len(TEL_HREF_RE.findall(t)) + len(DISPLAY_RE.findall(t)) + len(JSONLD_TEL_RE.findall(t))
        for t in files.values()
    )
    f = forms(cfg["digits"])
    print(
        f'OK: {total} phone occurrences across {len(SURFACES)} surfaces all agree '
        f'with site.config.json ({f["display"]})'
    )

    if cfg["placeholder"]:
        print(
            "\n"
            "  WARN ================================================================\n"
            f'  WARN  The shipped phone number {f["display"]} is a PLACEHOLDER.\n'
            "  WARN  Every click-to-call surface — including the sticky mobile\n"
            "  WARN  call bar — dials a number that does not exist. Leads die there.\n"
            "  WARN  Swap procedure: site.config.json header + PENDING_MANUAL.md\n"
            "  WARN  (client must provision the real line — Mike-gated).\n"
            "  WARN ================================================================\n"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
