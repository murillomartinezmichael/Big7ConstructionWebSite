"""
Design-token + typeface agreement contract across every shipped page.

Why: this repo has no build step and no shared stylesheet — the `no-build
rule` means every page inlines its own `<style>` block, so `:root` is
declared 6 times. Nothing stopped those copies from disagreeing, and by
2026-09-08 two of them had:

  * `404.html`          --ink-900: #1A1D22   (canonical is #0E1012)
  * `accessibility.html` --ink-900: #1A1D22
                         --ink-800: #22262B  (canonical is #151719)
                         --accent-500: #FF5A2D (canonical is #E85D2C)
                         --ink-300: #B7B0A5  (a warm grey that exists nowhere else)

...plus both pages loaded a *different* Google Fonts URL and set their
headings in `Anton`, a display face used on no other page of the site. A
visitor hitting a 404 or the accessibility statement saw a different brand
than the one on every other page.

That is invisible to all 25 existing suites: they check JSON-LD, SEO files,
redirects, contrast of individual hardcoded pairs, and the a11y baseline —
none of them compare pages against each other.

This closes that gap with three checks:
  1. Token agreement  — a custom property declared on more than one page
                        must carry the same value on every page.
  2. Typeface allowlist — no page may introduce a font family outside the
                        three the brand actually owns.
  3. Font URL agreement — every page that loads Google Fonts must request
                        the same family set, so no page renders in a
                        fallback face the others never use.

Stdlib only (`re`, `pathlib`, `sys`), matching the rest of tests/.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The three families the Big7 brand owns. `Fraunces` = headings/serif body,
# `Barlow Condensed` = eyebrows/labels, `Inter` = body. The `* Fallback`
# variants are the hand-authored metric-matched @font-face faces.
ALLOWED_FAMILIES = {
    "fraunces",
    "fraunces fallback",
    "fraunces display fallback",
    "barlow condensed",
    "barlow condensed fallback",
    "inter",
    "inter fallback",
}

# Generic / system keywords that are never a brand decision.
GENERIC_FAMILIES = {
    "sans-serif", "serif", "monospace", "system-ui", "ui-monospace", "cursive",
    "fantasy", "-apple-system", "blinkmacsystemfont", "georgia", "arial",
    "helvetica", "helvetica neue", "segoe ui", "roboto", "consolas", "menlo",
    "courier new", "times new roman", "impact", "inherit", "initial", "unset",
    "sfmono-regular", "sf mono", "liberation mono", "dejavu sans mono",
    "noto sans", "emoji", "apple color emoji", "segoe ui emoji",
}

ROOT_BLOCK_RE = re.compile(r":root\s*\{(.*?)\}", re.DOTALL)
DECL_RE = re.compile(r"(--[A-Za-z0-9-]+)\s*:\s*([^;]+);")
FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*([^;}]+)[;}]", re.IGNORECASE)
GFONTS_RE = re.compile(r"https://fonts\.googleapis\.com/css2\?([^\"']+)")


def shipped_pages(root: Path) -> list[Path]:
    """Every page the browser can reach. Sorted so failures read the same way twice."""
    return sorted(root.glob("*.html"))


def _families(decl: str) -> list[str]:
    """Split a font-family declaration into normalized family names."""
    out = []
    for part in decl.split(","):
        name = part.strip().strip("'\"").strip().lower()
        if name:
            out.append(name)
    return out


def check_token_agreement(pages: list[tuple[str, str]]) -> list[str]:
    """A custom property must not carry two different values across pages."""
    seen: dict[str, dict[str, list[str]]] = {}
    for name, html in pages:
        for block in ROOT_BLOCK_RE.findall(html):
            for var, raw in DECL_RE.findall(block):
                value = " ".join(raw.split()).lower()
                seen.setdefault(var, {}).setdefault(value, []).append(name)

    errors = []
    for var in sorted(seen):
        values = seen[var]
        if len(values) > 1:
            detail = "; ".join(
                f"{val} in {', '.join(sorted(files))}" for val, files in sorted(values.items())
            )
            errors.append(f"token `{var}` has {len(values)} different values across pages: {detail}")
    return errors


def check_typeface_allowlist(pages: list[tuple[str, str]]) -> list[str]:
    """No page may set type in a family outside the brand's three."""
    errors = []
    for name, html in pages:
        offenders: set[str] = set()
        for decl in FONT_FAMILY_RE.findall(html):
            for fam in _families(decl):
                if fam.startswith("var(") or fam in GENERIC_FAMILIES:
                    continue
                if fam not in ALLOWED_FAMILIES:
                    offenders.add(fam)
        for fam in sorted(offenders):
            errors.append(
                f"{name} sets type in `{fam}`, which is not one of the brand's "
                f"families ({', '.join(sorted(ALLOWED_FAMILIES))})"
            )
    return errors


def check_font_url_agreement(pages: list[tuple[str, str]]) -> list[str]:
    """Every page loading Google Fonts must request the same family set."""
    by_query: dict[str, list[str]] = {}
    for name, html in pages:
        queries = {m.group(1) for m in GFONTS_RE.finditer(html)}
        for q in queries:
            families = tuple(sorted(re.findall(r"family=([^&]+)", q)))
            by_query.setdefault("|".join(families), []).append(name)

    if len(by_query) > 1:
        detail = "; ".join(
            f"[{key}] on {', '.join(sorted(set(files)))}" for key, files in sorted(by_query.items())
        )
        return [f"pages request {len(by_query)} different Google Fonts family sets: {detail}"]
    return []


def run_all_checks(root: Path) -> list[str]:
    pages = [(p.name, p.read_text(encoding="utf-8")) for p in shipped_pages(root)]
    if not pages:
        return ["no shipped *.html pages found at repo root"]
    return (
        check_token_agreement(pages)
        + check_typeface_allowlist(pages)
        + check_font_url_agreement(pages)
    )


def selftest() -> int:
    """Mutate known-good input; every mutation must be caught by some check."""
    pages = [(p.name, p.read_text(encoding="utf-8")) for p in shipped_pages(REPO_ROOT)]
    not_caught: list[str] = []
    attempted: list[str] = []

    def add(label: str, mutated: list[tuple[str, str]], expect: str) -> None:
        attempted.append(label)
        errors = (
            check_token_agreement(mutated)
            + check_typeface_allowlist(mutated)
            + check_font_url_agreement(mutated)
        )
        if not any(expect in e for e in errors):
            not_caught.append(label)

    # 1. Re-introduce the exact ink-900 drift that shipped for weeks.
    drifted = []
    for name, html in pages:
        if name == "404.html":
            html = html.replace("--ink-900: #0E1012", "--ink-900: #1A1D22")
        drifted.append((name, html))
    add("404 --ink-900 drifts from canonical", drifted, "different values across pages")

    # 2. Re-introduce the rogue accent.
    drifted = []
    for name, html in pages:
        if name == "accessibility.html":
            html = html.replace("--accent-500: #E85D2C", "--accent-500: #FF5A2D")
        drifted.append((name, html))
    add("accessibility --accent-500 drifts", drifted, "different values across pages")

    # 3. Re-introduce Anton as a display face.
    drifted = []
    for name, html in pages:
        if name == "404.html":
            html = html.replace(
                "font-family: 'Fraunces', Georgia, serif;",
                "font-family: 'Anton', 'Impact', sans-serif;",
                1,
            )
        drifted.append((name, html))
    add("404 re-introduces Anton", drifted, "not one of the brand's")

    # 4. One page requests a different Google Fonts family set.
    drifted = []
    for name, html in pages:
        if name == "accessibility.html":
            html = html.replace("family=Fraunces", "family=Anton&family=Fraunces", 1)
        drifted.append((name, html))
    add("accessibility requests a different family set", drifted, "different Google Fonts family sets")

    if not_caught:
        print(f"SELFTEST: {len(not_caught)} mutation(s) not caught: {not_caught}")
        return 1
    print(f"SELFTEST: all {len(attempted)} mutations caught")
    return 0


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return selftest()

    errors = run_all_checks(REPO_ROOT)
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    pages = shipped_pages(REPO_ROOT)
    print(
        f"OK: one brand across every surface — custom properties agree on all "
        f"{len(pages)} shipped pages, type is set only in Fraunces / Barlow "
        f"Condensed / Inter, and every page requests the same Google Fonts "
        f"family set."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
