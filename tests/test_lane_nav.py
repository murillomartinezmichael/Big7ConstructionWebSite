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

# 2026-07-17 two-path restructure: Home Repair folded into the residential
# page (#home-repair section, 301 from the old URL) — two lanes remain.
# 2026-08-03 clean-URL migration: these are the HREF forms the pages must use
# — extensionless, matching the canonicals/sitemap/JSON-LD and what the live
# Cloudflare worker serves 200 on. The `.html` form 307s, so linking it would
# cost every homepage->lane click an extra hop. Rejecting `.html` here (rather
# than accepting both) is what stops the old shape drifting back.
LANE_PATHS = (
    "/commercial-industrial",
    "/residential-construction",
)

LANE_LABEL_HINT = {
    "/commercial-industrial": "commercial",
    "/residential-construction": "residential",
}


def _lane_file(lane_path: str) -> Path:
    """Clean URL -> the repo-root file that serves it (`/foo` -> `foo.html`).

    Mirrors tests/test_seo_files.py `_loc_to_repo_path`, so the nav contract
    and the sitemap contract resolve clean URLs the same way.
    """
    rel = lane_path.lstrip("/")
    direct = REPO_ROOT / rel
    if direct.is_file():
        return direct
    return REPO_ROOT / (rel + ".html")

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
        on_disk = _lane_file(lane)
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
        '<a href="/commercial-industrial">Commercial &amp; Industrial</a>'
        '<a href="/residential-construction">Residential Construction</a>'
        "</nav>"
        "<footer><ul>"
        '<li><a href="/commercial-industrial">Commercial &amp; Industrial</a></li>'
        '<li><a href="/residential-construction">Residential Construction</a></li>'
        "</ul></footer></body></html>"
    )
    lane_baseline = (
        "<html><body><main>content</main>"
        '<nav aria-label="Other lanes"><p>'
        '<a href="/residential-construction">Residential Construction</a> · '
        '<a href="/">All services</a></p></nav>'
        "</body></html>"
    )

    if check_index(idx_baseline):
        print("SELFTEST ABORT: index baseline fails check_index()", file=sys.stderr)
        return 1
    if check_lane_page("/commercial-industrial", lane_baseline):
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
                '<a href="/residential-construction">Residential Construction</a></nav>', "</nav>"
            ),
            "missing a link to '/residential-construction'",
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
                '<a href="/residential-construction">Residential Construction</a></nav>',
                '<a href="/commercial-industrial">dup</a></nav>',
            ),
            "more than once",
        ),
        (
            "footer lane link dropped",
            idx_baseline.replace(
                '<li><a href="/residential-construction">Residential Construction</a></li>', "", 1
            ),
            "footer sitemap is missing a link to '/residential-construction'",
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
                '<a href="/residential-construction">Residential Construction</a> · ', ""
            ),
            "missing sibling '/residential-construction'",
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
        errs = check_lane_page("/commercial-industrial", mutated)
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
        page = _lane_file(lane)
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
