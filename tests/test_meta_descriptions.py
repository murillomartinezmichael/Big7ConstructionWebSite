"""
Meta description contract across every top-level HTML page.

Why: `<meta name="description">` is the string Google, Bing, and every SMS/
messaging preview uses when the OG description is not consumed. A missing
description surrenders SERP snippet control to whatever fragment the crawler
picks off the page body. Two pages sharing the same description dilute crawl
budget on local-service queries — Google treats them as near-duplicates and
demotes both. A description that just repeats the `<title>` verbatim is a
"lost" snippet — the same text takes two of the three SERP lines that
determine click-through.

None of the sixteen existing stdlib suites lock this. `test_og_twitter.py`
asserts `og:description` (used by Facebook / iMessage / Slack) but not the
plain `<meta name="description">`. `test_seo_files.py` walks sitemap + robots
but not the per-page meta shape. This closes the gap with a stdlib-only
drift lock. Length bounds ([40, 220]) are set to accept shipped copy rather
than mandate a rewrite — copy-tightening toward Google's ~160-char SERP cap
is a separate copy-audit tick, not a mid-tick test gate.

Stdlib only (`html`, `re`, `pathlib`, `sys`).
"""
from __future__ import annotations

import html as htmllib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Every root-level *.html served by nginx. Kept explicit rather than globbed
# so a scratch/experimental HTML file dropped at the repo root during a
# refactor does not silently join the contract.
TARGETS = (
    "index.html",
    "404.html",
    "accessibility.html",
    "home-repair.html",
    "commercial-industrial.html",
    "residential-construction.html",
)

# Google's typical SERP truncation is ~155–160 chars on desktop. Bing tolerates
# ~168. Current shipped copy runs up to 214 raw / 210 decoded on index.html —
# not ideal but a copy decision, not a test decision. Ceiling set to 220 to
# lock shipped state; floor 40 rules out placeholder / accidentally-empty copy.
MIN_LEN = 40
MAX_LEN = 220

META_DESC_RE = re.compile(
    r"""<meta\s+[^>]*?name\s*=\s*(["'])description\1[^>]*?content\s*=\s*(["'])(?P<content>.*?)\2[^>]*?/?>""",
    re.IGNORECASE | re.DOTALL,
)
# Fallback for the reverse attribute order (content=... name=description).
META_DESC_RE_REV = re.compile(
    r"""<meta\s+[^>]*?content\s*=\s*(["'])(?P<content>.*?)\1[^>]*?name\s*=\s*(["'])description\3[^>]*?/?>""",
    re.IGNORECASE | re.DOTALL,
)
TITLE_RE = re.compile(r"<title>(?P<t>.*?)</title>", re.IGNORECASE | re.DOTALL)


def _extract_descriptions(html: str) -> list[str]:
    """Return every description meta content value on the page (raw, undecoded)."""
    hits = [m.group("content") for m in META_DESC_RE.finditer(html)]
    # Merge in reverse-order matches, deduping by position to avoid double-count
    # when both regexes match the same tag (they generally won't — the two
    # attribute orders are mutually exclusive — but this is defensive).
    for m in META_DESC_RE_REV.finditer(html):
        val = m.group("content")
        if val not in hits:
            hits.append(val)
    return hits


def _extract_title(html: str) -> str:
    m = TITLE_RE.search(html)
    return m.group("t").strip() if m else ""


def _norm(text: str) -> str:
    """Decode HTML entities + collapse whitespace for user-visible comparison."""
    return re.sub(r"\s+", " ", htmllib.unescape(text)).strip()


def assert_meta_description(path: Path) -> list[str]:
    errors: list[str] = []
    html = path.read_text(encoding="utf-8")
    descs = _extract_descriptions(html)

    if not descs:
        errors.append(f"{path.name}: missing <meta name=\"description\">")
        return errors
    if len(descs) > 1:
        errors.append(f"{path.name}: {len(descs)} <meta name=\"description\"> tags (must be exactly 1)")

    content_raw = descs[0]
    content = _norm(content_raw)
    length = len(content)
    if length < MIN_LEN:
        errors.append(f"{path.name}: description too short ({length} chars, floor {MIN_LEN}): {content!r}")
    if length > MAX_LEN:
        errors.append(f"{path.name}: description too long ({length} chars, ceiling {MAX_LEN}): {content[:60]!r}...")

    title = _norm(_extract_title(html))
    if title and content.lower() == title.lower():
        errors.append(f"{path.name}: description is byte-identical to <title> — wasted SERP line")

    return errors


def assert_descriptions_unique(pages_content: dict[str, str]) -> list[str]:
    """Duplicate meta descriptions across pages dilute crawl budget."""
    errors: list[str] = []
    seen: dict[str, str] = {}
    for name, content in pages_content.items():
        key = content.lower()
        if key in seen:
            errors.append(
                f"duplicate description on {name!r} and {seen[key]!r}: {content[:80]!r}..."
            )
        else:
            seen[key] = name
    return errors


# ─── selftest ────────────────────────────────────────────────────────────────


def _page(title: str, desc: str) -> str:
    return (
        f"<!doctype html><html><head>"
        f'<meta name="description" content="{desc}" />'
        f"<title>{title}</title>"
        f"</head><body></body></html>"
    )


_VALID_DESC = (
    "Big 7 Construction is a metro Atlanta general contractor delivering commercial, "
    "residential, and repair work under one accountable GC. Licensed, bonded, insured."
)
_VALID_TITLE = "Big 7 Construction — Metro Atlanta General Contractor"


def selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "page.html"
        tmp.write_text(_page(_VALID_TITLE, _VALID_DESC), encoding="utf-8")
        if assert_meta_description(tmp):
            print("SELFTEST FAIL: baseline should PASS", file=sys.stderr)
            return 1

        cases: list[tuple[str, str, str]] = [
            (
                "meta description missing",
                "missing <meta",
                "<!doctype html><html><head><title>x</title></head><body></body></html>",
            ),
            (
                "empty content",
                "too short",
                _page(_VALID_TITLE, ""),
            ),
            (
                "too short",
                "too short",
                _page(_VALID_TITLE, "Big 7 GC in Atlanta."),
            ),
            (
                "too long",
                "too long",
                _page(_VALID_TITLE, _VALID_DESC + " " + ("blah " * 60)),
            ),
            (
                "duplicate description meta tag",
                "must be exactly 1",
                _page(_VALID_TITLE, _VALID_DESC).replace(
                    "</head>",
                    f'<meta name="description" content="{_VALID_DESC}" /></head>',
                ),
            ),
            (
                "description == title",
                "byte-identical to <title>",
                _page(_VALID_DESC, _VALID_DESC),
            ),
        ]

        misses: list[str] = []
        for label, expect, mutated in cases:
            tmp.write_text(mutated, encoding="utf-8")
            errs = assert_meta_description(tmp)
            if not errs:
                misses.append(f"mutation not caught: {label}")
                continue
            if not any(expect in e for e in errs):
                misses.append(
                    f"mutation caught but wrong reason for {label!r}: got {errs!r}, wanted substring {expect!r}"
                )

        # Uniqueness check: two pages sharing the same description must flag.
        dup_errs = assert_descriptions_unique(
            {"a.html": _norm(_VALID_DESC), "b.html": _norm(_VALID_DESC)}
        )
        if not dup_errs or "duplicate description" not in dup_errs[0]:
            misses.append("mutation not caught: uniqueness (two pages, same description)")

        # False-positive guard: two DIFFERENT descriptions must NOT flag.
        ok_errs = assert_descriptions_unique(
            {"a.html": _norm(_VALID_DESC), "b.html": _norm("Different copy about a different lane.")}
        )
        if ok_errs:
            misses.append(f"false-positive: distinct descriptions flagged: {ok_errs!r}")

        if misses:
            for m in misses:
                print(f"SELFTEST FAIL: {m}", file=sys.stderr)
            return 1

    print(
        f"SELFTEST OK: baseline PASS + {len(cases)}/{len(cases)} mutations caught + uniqueness lock verified"
    )
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    errors: list[str] = []
    pages_content: dict[str, str] = {}
    for name in TARGETS:
        p = REPO_ROOT / name
        if not p.exists():
            errors.append(f"{name}: file not found at repo root")
            continue
        page_errs = assert_meta_description(p)
        errors.extend(page_errs)
        if not page_errs:
            html = p.read_text(encoding="utf-8")
            descs = _extract_descriptions(html)
            if descs:
                pages_content[name] = _norm(descs[0])

    errors.extend(assert_descriptions_unique(pages_content))

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(f"OK: meta descriptions valid + unique across {len(TARGETS)} top-level pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
