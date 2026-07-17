"""
404 lane-recovery contract.

Why: a visitor who typos a lane URL (`/commercial`, `/homerepair`,
`/residentialconstruction`) currently lands on 404.html. Before this
contract the only exit was a single "Back to Big 7" button pointing at
`/`, which sends the visitor back to the homepage's hero — one extra hop
+ a scan for the lane nav before they can reach the content they
originally asked for. That drop-off is invisible in analytics because
404 hits never carry a click-through label.

Locking three lane-recovery links on 404.html closes that gap: a
mistyped lane URL is one click from the actual lane page's own funnel
(each lane page carries its own `service:*` deep-links back to the
intake — locked separately by tests/test_conversion.py). Removing or
renaming a lane page without updating the 404 recovery list would
silently ship a broken navigation surface on the highest-traffic
error path.

Contract:
  1. 404.html carries a `<nav ... aria-label="Popular pages">` (or
     equivalent-labeled recovery region) — needed for AT users to skip
     over the recovery list, and it's the a11y-labelled hook the test
     keys off of so a stealth rename of `.lanes` doesn't slip through.
  2. Inside that nav, exactly one link per lane page exists:
       /commercial-industrial.html
       /residential-construction.html
       /residential-construction.html#home-repair (absorbed lane deep link)
  3. Each link's visible text is non-empty and mentions the lane by name
     (a link that reads "click here" fails a11y + wastes the recovery).
  4. Every lane path in the recovery list resolves to a real on-disk
     file at repo root (rename-safety net — the whole point of locking
     this is that a lane rename must break loudly).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FOURZEROFOUR = REPO_ROOT / "404.html"

# 2026-07-17 two-path restructure: Home Repair folded into the residential
# page — the recovery deep link targets the absorbed #home-repair section
# (the old /home-repair.html 301s there; a typo'd repair URL still recovers
# in one click). On-disk resolution strips the fragment.
LANE_PATHS = (
    "/commercial-industrial.html",
    "/residential-construction.html",
    "/residential-construction.html#home-repair",
)

# nav labelled "Popular pages" — matches the a11y label the 404 ships. Kept
# case-insensitive and whitespace-tolerant so a copy tweak ("popular pages",
# "Popular  pages") doesn't false-positive.
NAV_RE = re.compile(
    r'<nav\b[^>]*\baria-label="Popular pages"[^>]*>(?P<body>.*?)</nav>',
    re.IGNORECASE | re.DOTALL,
)
# Anchor tag with visible text captured. HREF captured separately so we can
# test both the destination and the label text.
ANCHOR_RE = re.compile(
    r'<a\b[^>]*\bhref="(?P<href>[^"]+)"[^>]*>(?P<text>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

# Substring each lane's visible link text must contain (case-insensitive).
# Guards against a stealth "click here" / "read more" rewrite of the recovery
# links that would degrade AT + visual scan-ability.
LANE_LABEL_HINT = {
    "/commercial-industrial.html": "commercial",
    "/residential-construction.html": "residential",
    "/residential-construction.html#home-repair": "home repair",
}


def _visible_text(inner_html: str) -> str:
    """Strip tags + entities → plain text for label-substring checks."""
    # Drop nested tags (arrows are usually inline spans / bare &rarr;).
    text = re.sub(r"<[^>]+>", "", inner_html)
    # Decode the handful of entities we actually emit; anything else stays
    # as-is because the substring check only cares about English words.
    text = text.replace("&amp;", "&").replace("&rarr;", "→")
    return re.sub(r"\s+", " ", text).strip()


def check(html: str) -> list[str]:
    errors: list[str] = []

    nav_match = NAV_RE.search(html)
    if not nav_match:
        errors.append(
            '404.html: no `<nav aria-label="Popular pages">` recovery region — '
            "typo'd lane URLs have no one-click route to the intended lane"
        )
        return errors

    nav_body = nav_match.group("body")
    hrefs: dict[str, str] = {}  # href → visible text
    for m in ANCHOR_RE.finditer(nav_body):
        href = m.group("href")
        text = _visible_text(m.group("text"))
        if href in hrefs:
            errors.append(
                f"404 recovery nav has duplicate link href={href!r} — "
                f"one lane listed twice, another lane silently missing"
            )
        hrefs[href] = text

    for lane in LANE_PATHS:
        if lane not in hrefs:
            errors.append(
                f"404 recovery nav is missing a link to {lane!r} — "
                f"typo'd URLs targeting this lane die on 404"
            )
            continue
        text = hrefs[lane]
        if not text:
            errors.append(
                f"404 recovery link to {lane!r} has empty visible text — "
                f"screen readers announce only the URL, not the destination"
            )
            continue
        hint = LANE_LABEL_HINT[lane]
        if hint not in text.lower():
            errors.append(
                f"404 recovery link to {lane!r} has text {text!r} — expected "
                f"to mention {hint!r} so a scan / AT reader identifies the lane"
            )

    for lane in LANE_PATHS:
        # Strip the leading slash so we can resolve against repo root.
        on_disk = REPO_ROOT / lane.lstrip("/").split("#", 1)[0]
        if not on_disk.is_file():
            errors.append(
                f"404 recovery lists {lane!r} but no file exists at {on_disk} — "
                f"lane was renamed / removed without updating 404 recovery"
            )

    return errors


def _selftest(_live_html: str) -> int:
    """Mutate a synthetic baseline N known-broken ways; each must be caught."""
    baseline = (
        "<html><body>"
        '<nav aria-label="Popular pages">'
        '<ul>'
        '<li><a href="/commercial-industrial.html">Commercial &amp; Industrial &rarr;</a></li>'
        '<li><a href="/residential-construction.html">Residential Construction &rarr;</a></li>'
        '<li><a href="/residential-construction.html#home-repair">Home Repair &amp; Improvements &rarr;</a></li>'
        '</ul></nav></body></html>'
    )
    baseline_errors = check(baseline)
    if baseline_errors:
        print("SELFTEST ABORT: synthetic baseline fails check():", file=sys.stderr)
        for e in baseline_errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    cases: list[tuple[str, str, str]] = [
        (
            "recovery nav removed entirely",
            re.sub(r'<nav[^>]*>.*?</nav>', "", baseline, flags=re.DOTALL),
            "no `<nav aria-label=\"Popular pages\">`",
        ),
        (
            "commercial-industrial lane recovery link dropped",
            baseline.replace(
                '<li><a href="/commercial-industrial.html">Commercial &amp; Industrial &rarr;</a></li>',
                "",
            ),
            "missing a link to '/commercial-industrial.html'",
        ),
        (
            "residential lane recovery link dropped",
            baseline.replace(
                '<li><a href="/residential-construction.html">Residential Construction &rarr;</a></li>',
                "",
            ),
            "missing a link to '/residential-construction.html'",
        ),
        (
            "home-repair deep-link recovery dropped",
            baseline.replace(
                '<li><a href="/residential-construction.html#home-repair">Home Repair &amp; Improvements &rarr;</a></li>',
                "",
            ),
            "missing a link to '/residential-construction.html#home-repair'",
        ),
        (
            "recovery link text rewritten to opaque 'click here'",
            baseline.replace(
                'Commercial &amp; Industrial &rarr;',
                'click here &rarr;',
            ),
            "expected to mention 'commercial'",
        ),
        (
            "recovery nav aria-label drifted (screen-reader landmark broken)",
            baseline.replace('aria-label="Popular pages"', 'aria-label="More"'),
            "no `<nav aria-label=\"Popular pages\">`",
        ),
        (
            "lane path listed twice (another lane silently missing)",
            baseline.replace(
                '<li><a href="/residential-construction.html#home-repair">Home Repair &amp; Improvements &rarr;</a></li>',
                '<li><a href="/commercial-industrial.html">dup</a></li>',
            ),
            "duplicate link href='/commercial-industrial.html'",
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
                f"{label}: mutation caught but no error contained {needle!r}. Got: {errs}"
            )

    if failures:
        for f in failures:
            print(f"SELFTEST FAIL: {f}", file=sys.stderr)
        return 1

    print(f"SELFTEST OK: {len(cases)} broken inputs all caught with the expected error.")
    return 0


def main(argv: list[str]) -> int:
    if not FOURZEROFOUR.exists():
        print(f"FAIL: {FOURZEROFOUR} not found", file=sys.stderr)
        return 1

    html = FOURZEROFOUR.read_text(encoding="utf-8")

    if "--selftest" in argv:
        return _selftest(html)

    errors = check(html)
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(
        f"OK: 404.html carries a labelled recovery nav with one-click "
        f"routes to all {len(LANE_PATHS)} lane pages "
        f"({', '.join(LANE_PATHS)})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
