"""
In-page anchor integrity contract test.

Why: every service-row, portfolio-card, nav item, and hero-CTA on
`index.html` uses fragment navigation (`href="#contact"`, `href="#hero"`,
etc.). A silent rename of any `<section id="contact">` — or a typo in a
new CTA — kills conversion without any test today catching it. The
existing five suites lock structured data, crawler discovery, meta tags,
the CTA→radio mapping, and on-disk asset bytes; none of them touch
whether the CTA's target actually exists on the page it points at.

Contract asserted:
  1. Every non-empty `href="#<name>"` resolves to at least one
     `id="<name>"` on the same page (case-sensitive per HTML5 §6.9.4).
  2. `#contact` — the sole money anchor — is referenced by at least
     MIN_CONTACT_REFS CTAs. Guards the regression where a refactor
     removes CTAs one at a time and nobody notices until the site
     stops taking bids.
  3. `#main` (the skip-link target) exists — WCAG 2.4.1.

Python 3.11+ stdlib only (`re`, `pathlib`, `sys`). No pip, no network.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "index.html"

# Regex: capture href="#anchor" (both quote styles). Excludes href="#" alone —
# that's a legitimate JS-handler noop pattern the spec permits, and this site
# does not currently use it, so flagging it would create false positives if
# someone adds an intentional one later.
HREF_ANCHOR_RE = re.compile(r'href\s*=\s*(?P<q>["\'])#(?P<name>[^"\'\s]+)(?P=q)')

# Regex: capture id="name" on any element. HTML5 allows unquoted ids; this
# codebase quotes them everywhere (verified in tick 14), so parse only the
# quoted form — matches the file today, and enforcing the quoted convention
# is itself a mild win.
ID_RE = re.compile(r'\bid\s*=\s*(?P<q>["\'])(?P<name>[^"\'\s]+)(?P=q)')

# Money anchor: #contact is the target of every service-row, portfolio-card,
# nav CTA, and hero CTA. If someone refactors away enough of them, the site
# stops taking bids and no other test notices. Threshold picked from today's
# floor (50 total anchor refs; ~30 of them point at #contact) with plenty of
# headroom so a legitimate CTA shuffle doesn't false-fail.
MIN_CONTACT_REFS = 10  # selftest fixture floor; real pages use PAGES below

# Per-page anchor contract (2026-07-17 two-path restructure): the chooser
# homepage keeps a handful of #contact CTAs (nav / mobile menu / hero /
# closer / lean contact); the CTA-dense surfaces are the lane pages.
# residential additionally must keep id="home-repair" — it is the 301
# target for the retired /home-repair.html.
PAGES = (
    ("index.html", 5, ("main", "contact")),
    ("commercial-industrial.html", 10, ("main", "contact")),
    ("residential-construction.html", 10, ("main", "contact", "home-repair")),
    # Case-study page (2026-07-20): no #contact section of its own — its
    # CTAs link cross-page to commercial-industrial.html#contact, which
    # HREF_ANCHOR_RE does not match (only bare href="#name"), so 0 is the
    # honest floor here.
    ("south-fulton-distribution.html", 0, ("main",)),
)

# Skip-link target — WCAG 2.4.1 "Bypass Blocks". Assert unconditionally so
# a future edit can't silently drop it.
REQUIRED_ANCHORS = ("main", "contact")

# Cross-page reachability lock (2026-07-20 fix): south-fulton-distribution.html
# shipped fully wired into sitemap/Dockerfile/OG/meta/a11y tests, but its ONLY
# inbound link was itself — the industrial-01 pf-card on
# commercial-industrial.html pointed href="#contact" instead of the case-study
# page, so a human could reach it only via a direct URL or SERP click (the
# same orphan-page bug class test_lane_nav.py locked for the two lane pages
# on 2026-07-16). Fixed by repointing the pf-card's href; this lock guards
# the fix against silent regression (e.g. a future portfolio-grid refactor
# reverting every card back to a uniform href="#contact").
CASE_STUDY_PAGE = "south-fulton-distribution.html"
CASE_STUDY_HOST_PAGE = "commercial-industrial.html"
CASE_STUDY_LINK_RE = re.compile(r'href="/?south-fulton-distribution\.html"', re.IGNORECASE)


def check_case_study_reachable(host_html: str) -> list[str]:
    """Return errors if commercial-industrial.html has no real link to the
    South Fulton case-study page. Empty list = PASS."""
    if CASE_STUDY_LINK_RE.search(host_html):
        return []
    return [
        f"{CASE_STUDY_HOST_PAGE} has no href to {CASE_STUDY_PAGE} — the "
        f"case-study page is orphaned (reachable only by direct URL/SERP)"
    ]


def check_anchors(
    html: str,
    min_contact_refs: int = MIN_CONTACT_REFS,
    required: tuple[str, ...] = REQUIRED_ANCHORS,
) -> list[str]:
    """Return a list of error strings. Empty list = PASS."""
    errors: list[str] = []

    href_names = [m.group("name") for m in HREF_ANCHOR_RE.finditer(html)]
    id_names = {m.group("name") for m in ID_RE.finditer(html)}

    if not href_names:
        errors.append("no href=\"#...\" anchor references found — page has no in-page navigation")
        return errors
    if not id_names:
        errors.append("no id=\"...\" attributes found — nothing to anchor to")
        return errors

    orphans: dict[str, int] = {}
    for name in href_names:
        if name not in id_names:
            orphans[name] = orphans.get(name, 0) + 1
    for name, count in sorted(orphans.items()):
        errors.append(
            f"orphan anchor href=\"#{name}\" ({count} occurrence{'s' if count > 1 else ''}) — "
            f"no id=\"{name}\" exists on the page"
        )

    for req in required:
        if req not in id_names:
            errors.append(f"required id=\"{req}\" is missing from the page")

    contact_ref_count = sum(1 for n in href_names if n == "contact")
    if contact_ref_count < min_contact_refs:
        errors.append(
            f"only {contact_ref_count} href=\"#contact\" references found, "
            f"expected >= {min_contact_refs} — CTAs may have been silently removed"
        )

    return errors


# ---------------------------------------------------------------------------
# Selftest — mutate a synthetic-but-realistic baseline and require each break
# to raise a specific error. Matches the tick-6/7/10/11/12/13 pattern.
# ---------------------------------------------------------------------------

def _baseline_html() -> str:
    """Small HTML doc that mimics the real site's anchor shape: 8 unique
    section ids, one skip-link target, and >= MIN_CONTACT_REFS #contact CTAs."""
    contact_ctas = "\n".join(
        f'    <a href="#contact" class="cta-{i}">Request a bid</a>'
        for i in range(MIN_CONTACT_REFS + 2)
    )
    return f"""<!doctype html>
<html><body>
  <a href="#main" class="skip-link">Skip to main content</a>
  <nav>
    <a href="#hero">Home</a>
    <a href="#services">Services</a>
    <a href="#portfolio">Portfolio</a>
    <a href="#credentials">Compliance</a>
    <a href="#process">Process</a>
    <a href="#testimonials">Reviews</a>
    <a href="#contact">Contact</a>
  </nav>
  <main id="main">
    <section id="hero"><h1>Hero</h1></section>
    <section id="services"><h2>Services</h2></section>
    <section id="portfolio"><h2>Portfolio</h2></section>
    <section id="credentials"><h2>Credentials</h2></section>
    <section id="process"><h2>Process</h2></section>
    <section id="testimonials"><h2>Testimonials</h2></section>
    <section id="contact"><h2>Contact</h2></section>
{contact_ctas}
  </main>
</body></html>"""


def _expect_pass(label: str, html: str) -> str | None:
    errs = check_anchors(html)
    if errs:
        return f"{label}: expected PASS, got errors: {errs}"
    return None


def _expect_fail(label: str, html: str, needle: str) -> str | None:
    errs = check_anchors(html)
    if not errs:
        return f"{label}: expected failure containing {needle!r}, got PASS"
    if not any(needle in e for e in errs):
        return f"{label}: expected failure containing {needle!r}, got errors: {errs}"
    return None


def selftest() -> int:
    baseline = _baseline_html()

    misses: list[str] = []

    baseline_err = _expect_pass("baseline", baseline)
    if baseline_err:
        misses.append(baseline_err)

    mutations: list[tuple[str, str, str]] = [
        (
            "orphan href to nonexistent target",
            baseline.replace('<a href="#hero">Home</a>', '<a href="#homepage">Home</a>'),
            'href="#homepage"',
        ),
        (
            "critical target renamed (#contact -> #quote)",
            baseline.replace('<section id="contact">', '<section id="quote">'),
            'href="#contact"',
        ),
        (
            "hero target deleted",
            baseline.replace('<section id="hero">', '<section id="landing">'),
            'href="#hero"',
        ),
        (
            "portfolio target deleted",
            baseline.replace('id="portfolio"', 'id="work"'),
            'href="#portfolio"',
        ),
        (
            "case mismatch (href=#Contact, id=contact)",
            baseline.replace('href="#contact"', 'href="#Contact"', 1),
            'href="#Contact"',
        ),
        (
            "typo in href",
            baseline.replace('href="#services"', 'href="#servces"'),
            'href="#servces"',
        ),
        (
            "skip-link target removed",
            baseline.replace('<main id="main">', "<main>"),
            'id="main"',
        ),
        (
            "contact CTAs mass-removed (below MIN_CONTACT_REFS)",
            re.sub(
                r'    <a href="#contact" class="cta-\d+">Request a bid</a>\n',
                "",
                baseline,
            ),
            f">= {MIN_CONTACT_REFS}",
        ),
    ]

    for label, mutated, needle in mutations:
        err = _expect_fail(label, mutated, needle)
        if err:
            misses.append(err)

    # check_case_study_reachable — separate mini-fixture (it inspects one
    # <a href> pattern on a host page, not the anchor-id contract above).
    host_baseline = '<a class="pf-card" href="/south-fulton-distribution.html" data-intent="portfolio:industrial-01">card</a>'
    if check_case_study_reachable(host_baseline):
        misses.append("case-study reachable baseline: expected PASS, got a failure")
    orphaned = host_baseline.replace('href="/south-fulton-distribution.html"', 'href="#contact"')
    orphan_errors = check_case_study_reachable(orphaned)
    if not orphan_errors or "orphaned" not in orphan_errors[0]:
        misses.append(f"case-study re-orphaned mutation: expected 'orphaned' failure, got {orphan_errors!r}")

    if misses:
        for m in misses:
            print(f"SELFTEST FAIL: {m}", file=sys.stderr)
        return 1

    print(f"SELFTEST OK: baseline PASS + {len(mutations)}/{len(mutations)} mutations caught + case-study reachability lock verified")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    failed = False
    total_refs = 0
    for name, floor, required in PAGES:
        path = REPO_ROOT / name
        if not path.exists():
            print(f"FAIL: {path} not found", file=sys.stderr)
            failed = True
            continue
        html = path.read_text(encoding="utf-8")
        errors = check_anchors(html, min_contact_refs=floor, required=required)
        if errors:
            for e in errors:
                print(f"FAIL: {name}: {e}", file=sys.stderr)
            failed = True
            continue
        total_refs += len(HREF_ANCHOR_RE.findall(html))
    if failed:
        return 1

    host_path = REPO_ROOT / CASE_STUDY_HOST_PAGE
    host_html = host_path.read_text(encoding="utf-8")
    case_study_errors = check_case_study_reachable(host_html)
    if case_study_errors:
        for e in case_study_errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(
        f"OK: {total_refs} href=\"#...\" references across {len(PAGES)} pages all "
        f"resolve to real ids; per-page #contact floors hold; skip-link, money "
        f"targets, and the residential #home-repair 301 target present; "
        f"{CASE_STUDY_PAGE} is human-reachable from {CASE_STUDY_HOST_PAGE}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
