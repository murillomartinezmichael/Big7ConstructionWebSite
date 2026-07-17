"""
LAW 11 WCAG 2.1 AA baseline contract across every top-level HTML page.

Locks six primitives on every root *.html: `<html lang="en">`, skip link
targeting `<main id="main">`, single `<main>` landmark, `prefers-reduced-motion`
@media rule, `:focus-visible` selector, footer/nav link to `/accessibility.html`
(exempt on accessibility.html itself). LAW 11 says "retro-fit on discovery — do
not defer" — this is the drift lock that enforces it at commit time.

No prior suite covers this: `test_anchors.py` locks skip-link -> #main on
index.html alone; every lane page is unguarded.

Stdlib only. Selftest + real-page golden run.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

TARGETS = (
    "index.html", "404.html", "accessibility.html",
    "commercial-industrial.html", "residential-construction.html",
)

HTML_LANG_RE = re.compile(r"""<html\b[^>]*\blang\s*=\s*(["'])(?P<lang>[^"']+)\1""", re.IGNORECASE)
SKIP_LINK_RE = re.compile(
    r"""<a\b[^>]*\bclass\s*=\s*(["'])[^"']*\bskip-link\b[^"']*\1[^>]*\bhref\s*=\s*(["'])(?P<href>#[^"']+)\2""",
    re.IGNORECASE,
)
SKIP_LINK_RE_REV = re.compile(
    r"""<a\b[^>]*\bhref\s*=\s*(["'])(?P<href>#[^"']+)\1[^>]*\bclass\s*=\s*(["'])[^"']*\bskip-link\b[^"']*\3""",
    re.IGNORECASE,
)
MAIN_LANDMARK_RE = re.compile(r"""<main\b[^>]*\bid\s*=\s*(["'])main\1""", re.IGNORECASE)
ANY_MAIN_RE = re.compile(r"<main\b", re.IGNORECASE)
REDUCED_MOTION_RE = re.compile(r"@media\s*\([^)]*prefers-reduced-motion\s*:\s*reduce", re.IGNORECASE)
FOCUS_VISIBLE_RE = re.compile(r":focus-visible", re.IGNORECASE)
ACCESSIBILITY_LINK_RE = re.compile(
    r"""<a\b[^>]*\bhref\s*=\s*(["'])(?P<href>[^"']*accessibility(?:\.html)?(?:#[^"']*)?)\1""",
    re.IGNORECASE,
)


def _find_skip_link(html: str) -> str | None:
    m = SKIP_LINK_RE.search(html) or SKIP_LINK_RE_REV.search(html)
    return m.group("href") if m else None


def assert_a11y_baseline(html: str, label: str, *, is_accessibility_page: bool = False) -> list[str]:
    errors: list[str] = []

    lang_m = HTML_LANG_RE.search(html)
    if lang_m is None:
        errors.append(f"{label}: missing lang attribute on <html> (WCAG 3.1.1)")
    elif not lang_m.group("lang").lower().startswith("en"):
        errors.append(f"{label}: <html lang> must start with 'en', got {lang_m.group('lang')!r}")

    skip_href = _find_skip_link(html)
    if skip_href is None:
        errors.append(f"{label}: missing <a class=\"skip-link\" href=\"#...\"> (WCAG 2.4.1)")

    main_landmarks = MAIN_LANDMARK_RE.findall(html)
    any_mains = ANY_MAIN_RE.findall(html)
    if not main_landmarks:
        errors.append(f"{label}: missing <main id=\"main\"> landmark (WCAG 1.3.1)")
    elif len(any_mains) > 1:
        errors.append(f"{label}: {len(any_mains)} <main> elements found (WCAG 1.3.1 wants one)")

    if skip_href is not None and main_landmarks and skip_href != "#main":
        errors.append(f"{label}: skip-link href={skip_href!r} but <main id=\"main\"> — target drift")

    if not REDUCED_MOTION_RE.search(html):
        errors.append(f"{label}: missing `@media (prefers-reduced-motion: reduce)` (WCAG 2.3.3)")

    if not FOCUS_VISIBLE_RE.search(html):
        errors.append(f"{label}: missing `:focus-visible` selector (WCAG 2.4.7)")

    if not is_accessibility_page and not ACCESSIBILITY_LINK_RE.search(html):
        errors.append(f"{label}: no <a href=\"...accessibility...\"> found (LAW 11 statement-page reachability)")

    return errors


def _valid_html() -> str:
    return """<!doctype html>
<html lang="en">
<head><style>
  :focus-visible { outline: 2px solid #f60; }
  @media (prefers-reduced-motion: reduce) { * { animation-duration: 0.01ms !important; } }
</style></head>
<body>
  <a class="skip-link" href="#main">Skip to main content</a>
  <nav><a href="/accessibility.html">Accessibility</a></nav>
  <main id="main">Content here.</main>
</body></html>"""


def selftest() -> int:
    baseline = _valid_html()
    if assert_a11y_baseline(baseline, "baseline"):
        print("SELFTEST FAIL: baseline should be valid", file=sys.stderr)
        return 1

    cases: list[tuple[str, str, str]] = [
        ("lang missing", baseline.replace('<html lang="en">', "<html>"), "missing lang"),
        ("lang non-english", baseline.replace('lang="en"', 'lang="es"'), "must start with 'en'"),
        ("skip link removed",
         baseline.replace('<a class="skip-link" href="#main">Skip to main content</a>', ""),
         "missing <a class=\"skip-link\""),
        ("skip link href drift",
         baseline.replace('href="#main">Skip', 'href="#content">Skip'),
         "target drift"),
        ("<main id=main> removed",
         baseline.replace('<main id="main">Content here.</main>', "<div>Content here.</div>"),
         "missing <main id=\"main\">"),
        ("two <main> elements",
         baseline.replace('<main id="main">Content here.</main>',
                          '<main id="main">A</main><main>B</main>'),
         "2 <main> elements"),
        ("prefers-reduced-motion removed",
         re.sub(r"@media[^{]*prefers-reduced-motion[^}]*\}[^}]*\}", "", baseline),
         "prefers-reduced-motion"),
        (":focus-visible removed",
         baseline.replace(":focus-visible", ":hover"),
         ":focus-visible"),
        ("accessibility link removed",
         re.sub(r'<a[^>]*href="[^"]*accessibility[^"]*"[^>]*>[^<]*</a>', "", baseline),
         "no <a href=\"...accessibility"),
    ]

    failures: list[str] = []
    for name, mutated, expected in cases:
        errs = assert_a11y_baseline(mutated, name)
        if not errs:
            failures.append(f"not caught: {name}")
        elif not any(expected in e for e in errs):
            failures.append(f"wrong error for {name}: expected {expected!r}, got {errs!r}")

    # False-positive guard: accessibility page is exempt from the self-link check.
    a11y_page = re.sub(r'<a[^>]*href="[^"]*accessibility[^"]*"[^>]*>[^<]*</a>', "", baseline)
    if assert_a11y_baseline(a11y_page, "a11y-page", is_accessibility_page=True):
        failures.append("false positive: accessibility page flagged for self-link exemption")

    if failures:
        for f in failures:
            print(f"SELFTEST FAIL: {f}", file=sys.stderr)
        return 1

    print(f"SELFTEST OK: baseline PASS + {len(cases)}/{len(cases)} mutations caught + a11y-page exemption honored")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    errors: list[str] = []
    for name in TARGETS:
        path = REPO_ROOT / name
        if not path.exists():
            errors.append(f"{name}: not found at {path}")
            continue
        errors.extend(assert_a11y_baseline(
            path.read_text(encoding="utf-8"),
            name,
            is_accessibility_page=(name == "accessibility.html"),
        ))

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(
        f"OK: LAW 11 a11y baseline holds on {len(TARGETS)} top-level pages "
        f"(lang=en, skip-link -> #main, <main>, prefers-reduced-motion, :focus-visible, /accessibility link)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
