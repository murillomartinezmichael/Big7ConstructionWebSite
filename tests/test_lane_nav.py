"""
Lane navigability contract — homepage → lane pages → sibling lanes.

Why: the three lane pages shipped (ticks 17/22/23) with sitemap entries,
Service JSON-LD, OG cards, and Dockerfile COPYs — but until 2026-07-16 the
ONLY references to them on index.html lived inside JSON-LD blocks. No human
could click from the homepage to a lane page: they were orphan pages,
reachable via SERP or a typo'd-URL 404 recovery (tests/test_404_lane_recovery.py)
but invisible to the primary navigation. "Three lanes navigable on one
domain" is the W2 definition of done; JSON-LD-only references don't satisfy
it. This contract locks the human-clickable surface so a refactor can't
silently re-orphan the lanes while every SEO-surface test stays green.

Contract:
  1. index.html carries a `<nav aria-label="Buyer lanes">` region with
     exactly one link per lane page, each labeled by lane name (no
     "click here" rewrites), no duplicates.
  2. index.html's `<footer>` also links all three lane pages (second
     discovery surface — visitors who scroll past Services).
  3. Every lane page carries a `<nav aria-label="Other lanes">` region
     linking BOTH sibling lane pages and `/` (no dead-end lanes).
  4. Every lane path referenced resolves to a real on-disk file at repo
     root (rename-safety net).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "index.html"

LANE_PATHS = (
    "/commercial-industrial.html",
    "/residential-construction.html",
    "/home-repair.html",
)

LANE_LABEL_HINT = {
    "/commercial-industrial.html": "commercial",
    "/residential-construction.html": "residential",
    "/home-repair.html": "home repair",
}

BUYER_NAV_RE = re.compile(
    r'<nav\b[^>]*\baria-label="Buyer lanes"[^>]*>(?P<body>.*?)</nav>',
    re.IGNORECASE | re.DOTALL,
)
OTHER_NAV_RE = re.compile(
    r'<nav\b[^>]*\baria-label="Other lanes"[^>]*>(?P<body>.*?)</nav>',
    re.IGNORECASE | re.DOTALL,
)
FOOTER_RE = re.compile(r"<footer\b[^>]*>(?P<body>.*?)</footer>", re.IGNORECASE | re.DOTALL)
ANCHOR_RE = re.compile(
    r'<a\b[^>]*\bhref="(?P<href>[^"]+)"[^>]*>(?P<text>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)


def _visible_text(inner_html: str) -> str:
    text = re.sub(r"<[^>]+>", "", inner_html)
    text = text.replace("&amp;", "&").replace("&rarr;", "→")
    return re.sub(r"\s+", " ", text).strip()


def _anchors(html_fragment: str) -> dict[str, str]:
    """href → visible text; flags duplicates by returning them in `dupes`."""
    out: dict[str, str] = {}
    for m in ANCHOR_RE.finditer(html_fragment):
        out.setdefault(m.group("href"), _visible_text(m.group("text")))
    return out


def check_index(html: str) -> list[str]:
    errors: list[str] = []

    nav_match = BUYER_NAV_RE.search(html)
    if not nav_match:
        errors.append(
            'index.html: no `<nav aria-label="Buyer lanes">` region — '
            "lane pages are orphans again (JSON-LD references don't count as navigation)"
        )
    else:
        body = nav_match.group("body")
        seen: list[str] = [m.group("href") for m in ANCHOR_RE.finditer(body)]
        for lane in LANE_PATHS:
            if seen.count(lane) > 1:
                errors.append(
                    f"index.html Buyer-lanes nav lists {lane!r} more than once — "
                    f"one lane duplicated, another likely missing"
                )
            if lane not in seen:
                errors.append(
                    f"index.html Buyer-lanes nav is missing a link to {lane!r}"
                )
                continue
            text = _anchors(body).get(lane, "")
            hint = LANE_LABEL_HINT[lane]
            if hint not in text.lower():
                errors.append(
                    f"index.html Buyer-lanes link to {lane!r} has text {text!r} — "
                    f"expected to mention {hint!r}"
                )

    footer_match = FOOTER_RE.search(html)
    if not footer_match:
        errors.append("index.html: no <footer> found")
    else:
        foot_hrefs = _anchors(footer_match.group("body"))
        for lane in LANE_PATHS:
            if lane not in foot_hrefs:
                errors.append(
                    f"index.html footer sitemap is missing a link to {lane!r} — "
                    f"below-the-fold discovery surface dropped"
                )

    return errors


def check_lane_page(page_path: str, html: str) -> list[str]:
    errors: list[str] = []
    siblings = [p for p in LANE_PATHS if p != page_path]

    nav_match = OTHER_NAV_RE.search(html)
    if not nav_match:
        errors.append(
            f'{page_path.lstrip("/")}: no `<nav aria-label="Other lanes">` region — '
            f"wrong-lane visitors have no cross-route and bounce"
        )
        return errors

    hrefs = _anchors(nav_match.group("body"))
    for sib in siblings:
        if sib not in hrefs:
            errors.append(
                f'{page_path.lstrip("/")}: Other-lanes nav is missing sibling {sib!r}'
            )
    if "/" not in hrefs:
        errors.append(
            f'{page_path.lstrip("/")}: Other-lanes nav is missing the "/" all-services link'
        )
    return errors


def check_on_disk() -> list[str]:
    errors: list[str] = []
    for lane in LANE_PATHS:
        on_disk = REPO_ROOT / lane.lstrip("/")
        if not on_disk.is_file():
            errors.append(
                f"lane page {lane!r} referenced by the nav contract does not exist "
                f"at {on_disk} — renamed/removed without updating navigation"
            )
    return errors


def _selftest() -> int:
    idx_baseline = (
        "<html><body>"
        '<nav aria-label="Buyer lanes">'
        '<a href="/commercial-industrial.html">Commercial &amp; Industrial</a>'
        '<a href="/residential-construction.html">Residential Construction</a>'
        '<a href="/home-repair.html">Home Repair &amp; Improvements</a>'
        "</nav>"
        "<footer><ul>"
        '<li><a href="/commercial-industrial.html">Commercial &amp; Industrial</a></li>'
        '<li><a href="/residential-construction.html">Residential Construction</a></li>'
        '<li><a href="/home-repair.html">Home Repair &amp; Improvements</a></li>'
        "</ul></footer></body></html>"
    )
    lane_baseline = (
        "<html><body><main>content</main>"
        '<nav aria-label="Other lanes"><p>'
        '<a href="/residential-construction.html">Residential Construction</a> · '
        '<a href="/home-repair.html">Home Repair</a> · '
        '<a href="/">All services</a></p></nav>'
        "</body></html>"
    )

    if check_index(idx_baseline):
        print("SELFTEST ABORT: index baseline fails check_index()", file=sys.stderr)
        return 1
    if check_lane_page("/commercial-industrial.html", lane_baseline):
        print("SELFTEST ABORT: lane baseline fails check_lane_page()", file=sys.stderr)
        return 1

    failures: list[str] = []

    idx_cases = [
        (
            "Buyer-lanes nav removed entirely (lanes re-orphaned)",
            re.sub(r'<nav aria-label="Buyer lanes">.*?</nav>', "", idx_baseline, flags=re.DOTALL),
            'no `<nav aria-label="Buyer lanes">`',
        ),
        (
            "one lane dropped from Buyer-lanes nav",
            idx_baseline.replace(
                '<a href="/home-repair.html">Home Repair &amp; Improvements</a></nav>', "</nav>"
            ),
            "missing a link to '/home-repair.html'",
        ),
        (
            "lane link text rewritten opaque",
            idx_baseline.replace(
                ">Commercial &amp; Industrial</a>", ">click here</a>", 1
            ),
            "expected to mention 'commercial'",
        ),
        (
            "same lane listed twice in Buyer-lanes nav",
            idx_baseline.replace(
                '<a href="/home-repair.html">Home Repair &amp; Improvements</a></nav>',
                '<a href="/commercial-industrial.html">dup</a></nav>',
            ),
            "more than once",
        ),
        (
            "footer lane link dropped",
            idx_baseline.replace(
                '<li><a href="/residential-construction.html">Residential Construction</a></li>', "", 1
            ),
            "footer sitemap is missing a link to '/residential-construction.html'",
        ),
    ]
    for label, mutated, needle in idx_cases:
        if mutated == idx_baseline:
            failures.append(f"{label}: mutation was a no-op")
            continue
        errs = check_index(mutated)
        if not errs:
            failures.append(f"{label}: slipped through")
        elif not any(needle in e for e in errs):
            failures.append(f"{label}: caught but no error contained {needle!r}. Got: {errs}")

    lane_cases = [
        (
            "Other-lanes nav removed from a lane page",
            re.sub(r'<nav aria-label="Other lanes">.*?</nav>', "", lane_baseline, flags=re.DOTALL),
            'no `<nav aria-label="Other lanes">`',
        ),
        (
            "sibling link dropped from Other-lanes nav",
            lane_baseline.replace(
                '<a href="/residential-construction.html">Residential Construction</a> · ', ""
            ),
            "missing sibling '/residential-construction.html'",
        ),
        (
            "all-services link dropped from Other-lanes nav",
            lane_baseline.replace(' · <a href="/">All services</a>', ""),
            'missing the "/" all-services link',
        ),
    ]
    for label, mutated, needle in lane_cases:
        if mutated == lane_baseline:
            failures.append(f"{label}: mutation was a no-op")
            continue
        errs = check_lane_page("/commercial-industrial.html", mutated)
        if not errs:
            failures.append(f"{label}: slipped through")
        elif not any(needle in e for e in errs):
            failures.append(f"{label}: caught but no error contained {needle!r}. Got: {errs}")

    if failures:
        for f in failures:
            print(f"SELFTEST FAIL: {f}", file=sys.stderr)
        return 1

    print(
        f"SELFTEST OK: {len(idx_cases) + len(lane_cases)} broken inputs all caught "
        f"with the expected error."
    )
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()

    errors: list[str] = []
    if not INDEX.exists():
        print(f"FAIL: {INDEX} not found", file=sys.stderr)
        return 1
    errors += check_index(INDEX.read_text(encoding="utf-8"))

    for lane in LANE_PATHS:
        page = REPO_ROOT / lane.lstrip("/")
        if not page.exists():
            errors.append(f"lane page {lane!r} missing on disk")
            continue
        errors += check_lane_page(lane, page.read_text(encoding="utf-8"))

    errors += check_on_disk()

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(
        f"OK: index.html routes humans to all {len(LANE_PATHS)} lane pages "
        f"(Buyer-lanes nav + footer), and every lane page cross-links both "
        f"siblings + / (no orphan lanes, no dead ends)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
