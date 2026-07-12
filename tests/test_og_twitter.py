"""
Open Graph + Twitter card meta-tag contract test.

Why: OG + Twitter tags drive how the site previews in iMessage, Slack, Facebook,
LinkedIn, and every text-message client — a silent regression turns high-intent
shares into blank-preview link rot. STANDARDS §6 explicitly names "meta/OG tags
real (paste URL into a chat app — does the preview look pro?)" as a deploy gate.

Locks the tick-4 branded-card fix: asserts `og:image` and `twitter:image` point
at the 1200x630 `images/og-card.png` and NOT the 206px `images/jobsite-01.jpg`
placeholder (Slack/iMessage/Facebook crop the placeholder into a smear).
Same guard doctrine as `test_jsonld.py`'s image/logo lock.

Also locks (tick 19) the <link rel="canonical" href="..."> ↔ og:url agreement
per page. If they disagree, Google indexes one URL while every social share
previews under another — a classic silent SEO leak. Exception: 404.html carries
NO canonical link (Google's "soft-404 canonicals confuse crawlers" guidance)
while its og:url still points social clicks at the homepage.

Runs against every top-level HTML file: `index.html`, `404.html`,
`accessibility.html`, `home-repair.html`, `commercial-industrial.html`,
`residential-construction.html`. Adding a new top-level page? Append it to
`TARGETS` and — unless it's a 404-style error page — to `TARGETS_WITH_CANONICAL`.

Python 3.11+ stdlib only (`re`, `pathlib`). No pip install, no network.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "index.html"
NOT_FOUND = REPO_ROOT / "404.html"
ACCESSIBILITY = REPO_ROOT / "accessibility.html"
HOME_REPAIR = REPO_ROOT / "home-repair.html"
COMMERCIAL_INDUSTRIAL = REPO_ROOT / "commercial-industrial.html"
RESIDENTIAL_CONSTRUCTION = REPO_ROOT / "residential-construction.html"
TARGETS = (INDEX, NOT_FOUND, ACCESSIBILITY, HOME_REPAIR, COMMERCIAL_INDUSTRIAL, RESIDENTIAL_CONSTRUCTION)
# Pages that MUST carry <link rel="canonical" href="..."> matching og:url.
# 404.html is excluded on purpose — see NO_CANONICAL_PAGES below.
TARGETS_WITH_CANONICAL = (INDEX, ACCESSIBILITY, HOME_REPAIR, COMMERCIAL_INDUSTRIAL, RESIDENTIAL_CONSTRUCTION)
# Pages that MUST NOT carry a canonical link at all. Google's guidance is that
# soft-404s pointing at themselves confuse the crawler; pointing at the homepage
# risks the 404 URL absorbing homepage rankings on strange edge cases. Simplest
# safe answer: no canonical on the 404, but keep og:url → homepage so social
# clicks still land somewhere real.
NO_CANONICAL_PAGES = (NOT_FOUND,)

# Match each <meta ...> tag broadly, then pull attributes in a second pass.
# Attribute regexes use a matched-quote backreference so an apostrophe inside a
# double-quoted content string (e.g. "This isn't live.") doesn't break parsing.
META_TAG_RE = re.compile(r'<meta\b[^>]*/?>', re.IGNORECASE)
ATTR_KEY_RE = re.compile(
    r'\b(?:property|name)\s*=\s*(?P<q>["\'])(?P<val>[^"\']+)(?P=q)',
    re.IGNORECASE,
)
ATTR_CONTENT_RE = re.compile(
    r'\bcontent\s*=\s*(?P<q>["\'])(?P<val>.*?)(?P=q)',
    re.IGNORECASE | re.DOTALL,
)
LINK_TAG_RE = re.compile(r'<link\b[^>]*/?>', re.IGNORECASE)
LINK_REL_RE = re.compile(
    r'\brel\s*=\s*(?P<q>["\'])(?P<val>[^"\']+)(?P=q)',
    re.IGNORECASE,
)
LINK_HREF_RE = re.compile(
    r'\bhref\s*=\s*(?P<q>["\'])(?P<val>[^"\']+)(?P=q)',
    re.IGNORECASE,
)

REQUIRED_OG = {"og:type", "og:title", "og:description", "og:url", "og:image"}
REQUIRED_TWITTER = {"twitter:card", "twitter:title", "twitter:description", "twitter:image"}

BRAND_CARD = "og-card.png"
PLACEHOLDER = "jobsite-01.jpg"
EXPECTED_OG_IMAGE_WIDTH = "1200"
EXPECTED_OG_IMAGE_HEIGHT = "630"
EXPECTED_OG_IMAGE_TYPE = "image/png"
EXPECTED_TWITTER_CARD = "summary_large_image"


def extract_meta(html: str) -> dict[str, str]:
    tags: dict[str, str] = {}
    for tag in META_TAG_RE.findall(html):
        key_m = ATTR_KEY_RE.search(tag)
        content_m = ATTR_CONTENT_RE.search(tag)
        if key_m is None or content_m is None:
            continue
        tags[key_m.group("val").lower()] = content_m.group("val")
    return tags


def extract_canonicals(html: str) -> list[str]:
    """Return every <link rel="canonical" href="..."> href on the page.

    Returns a list (not a single value) so the test can catch the "two conflicting
    canonicals were left on the page" case, which some CMS copy-paste bugs cause.
    """
    hrefs: list[str] = []
    for tag in LINK_TAG_RE.findall(html):
        rel_m = LINK_REL_RE.search(tag)
        href_m = LINK_HREF_RE.search(tag)
        if rel_m is None or href_m is None:
            continue
        # rel can be space-separated ("canonical alternate"); check tokens.
        rel_tokens = rel_m.group("val").lower().split()
        if "canonical" in rel_tokens:
            hrefs.append(href_m.group("val"))
    return hrefs


def assert_og_twitter(tags: dict[str, str], label: str) -> list[str]:
    errors: list[str] = []

    missing_og = REQUIRED_OG - tags.keys()
    if missing_og:
        errors.append(f"{label}: missing OG tags: {sorted(missing_og)}")
    missing_tw = REQUIRED_TWITTER - tags.keys()
    if missing_tw:
        errors.append(f"{label}: missing Twitter tags: {sorted(missing_tw)}")

    og_url = tags.get("og:url", "")
    if og_url and not og_url.startswith("https://"):
        errors.append(f"{label}: og:url must be absolute https, got {og_url!r}")

    og_image = tags.get("og:image", "")
    if og_image:
        if not og_image.startswith("https://"):
            errors.append(f"{label}: og:image must be absolute https, got {og_image!r}")
        if PLACEHOLDER in og_image:
            errors.append(
                f"{label}: og:image points at 206px placeholder {PLACEHOLDER!r} — "
                f"tick 4 (2026-07-06) moved this off to the branded 1200x630 og-card.png. "
                f"Preview crops turn the placeholder into a smear on Slack/iMessage/Facebook."
            )
        elif BRAND_CARD not in og_image:
            errors.append(
                f"{label}: og:image should reference {BRAND_CARD!r} (the branded 1200x630 "
                f"card generated by scripts/gen-og-card.py), got {og_image!r}"
            )

    tw_card = tags.get("twitter:card", "")
    if tw_card and tw_card != EXPECTED_TWITTER_CARD:
        errors.append(
            f"{label}: twitter:card must be {EXPECTED_TWITTER_CARD!r} to preview the "
            f"1200x630 card without cropping, got {tw_card!r}"
        )

    tw_image = tags.get("twitter:image", "")
    if tw_image:
        if not tw_image.startswith("https://"):
            errors.append(f"{label}: twitter:image must be absolute https, got {tw_image!r}")
        if PLACEHOLDER in tw_image:
            errors.append(
                f"{label}: twitter:image points at 206px placeholder {PLACEHOLDER!r} — "
                f"same rationale as og:image."
            )

    # Only assert width/height/type when og:image is present. If og:image itself is
    # missing, the "missing OG tags" error above is the real signal; dumping three
    # more "og:image:width missing" errors underneath would just be noise.
    if og_image:
        w = tags.get("og:image:width")
        if w != EXPECTED_OG_IMAGE_WIDTH:
            errors.append(f"{label}: og:image:width must be {EXPECTED_OG_IMAGE_WIDTH!r}, got {w!r}")
        h = tags.get("og:image:height")
        if h != EXPECTED_OG_IMAGE_HEIGHT:
            errors.append(f"{label}: og:image:height must be {EXPECTED_OG_IMAGE_HEIGHT!r}, got {h!r}")
        t = tags.get("og:image:type")
        if t != EXPECTED_OG_IMAGE_TYPE:
            errors.append(f"{label}: og:image:type must be {EXPECTED_OG_IMAGE_TYPE!r}, got {t!r}")

    return errors


def assert_canonical(
    canonicals: list[str],
    og_url: str,
    label: str,
    *,
    must_have_canonical: bool,
) -> list[str]:
    """Enforce the canonical/og:url contract.

    - Pages in TARGETS_WITH_CANONICAL: exactly one canonical link, equal to og:url.
    - Pages in NO_CANONICAL_PAGES: zero canonical links (see NO_CANONICAL_PAGES doc).
    """
    errors: list[str] = []
    if must_have_canonical:
        if not canonicals:
            errors.append(
                f"{label}: missing <link rel=\"canonical\" href=\"...\"> — "
                f"required so Google indexes the URL that og:url promises social clicks"
            )
            return errors
        if len(canonicals) > 1:
            errors.append(
                f"{label}: {len(canonicals)} canonical <link> tags found "
                f"({canonicals!r}) — only one is allowed; Google will pick nondeterministically"
            )
        canonical = canonicals[0]
        if not canonical.startswith("https://"):
            errors.append(f"{label}: canonical must be absolute https, got {canonical!r}")
        if og_url and canonical != og_url:
            errors.append(
                f"{label}: canonical / og:url disagree — "
                f"canonical={canonical!r} vs og:url={og_url!r}. "
                f"Google will index one URL while social shares preview under another."
            )
    else:
        if canonicals:
            errors.append(
                f"{label}: page is in NO_CANONICAL_PAGES but carries "
                f"{len(canonicals)} canonical link(s) ({canonicals!r}). "
                f"404s must not self-canonicalize; see NO_CANONICAL_PAGES doc."
            )
    return errors


def _valid_tags() -> dict[str, str]:
    """Minimal-but-valid tag set used as the selftest baseline."""
    return {
        "og:type": "website",
        "og:title": "Big 7 Construction — Commercial · Industrial · Residential",
        "og:description": "Two divisions, every trade in-house.",
        "og:url": "https://big7construction.com/",
        "og:image": "https://big7construction.com/images/og-card.png",
        "og:image:width": EXPECTED_OG_IMAGE_WIDTH,
        "og:image:height": EXPECTED_OG_IMAGE_HEIGHT,
        "og:image:type": EXPECTED_OG_IMAGE_TYPE,
        "twitter:card": EXPECTED_TWITTER_CARD,
        "twitter:title": "Big 7 Construction",
        "twitter:description": "Two divisions, every trade in-house.",
        "twitter:image": "https://big7construction.com/images/og-card.png",
    }


def selftest() -> int:
    baseline = _valid_tags()
    if assert_og_twitter(baseline, "selftest-baseline"):
        print("SELFTEST FAIL: baseline should be valid", file=sys.stderr)
        return 1

    cases: list[tuple[str, dict[str, str]]] = []
    b = _valid_tags(); b.pop("og:title"); cases.append(("og:title missing", b))
    b = _valid_tags(); b.pop("og:image"); cases.append(("og:image missing", b))
    b = _valid_tags(); b.pop("twitter:card"); cases.append(("twitter:card missing", b))
    b = _valid_tags(); b.pop("twitter:image"); cases.append(("twitter:image missing", b))
    b = _valid_tags(); b["og:url"] = "http://big7construction.com/"; cases.append(("og:url not https", b))
    b = _valid_tags(); b["og:image"] = "https://big7construction.com/images/jobsite-01.jpg"; cases.append(("og:image is 206px placeholder", b))
    b = _valid_tags(); b["og:image"] = "https://big7construction.com/images/random.png"; cases.append(("og:image not branded card", b))
    b = _valid_tags(); b["twitter:card"] = "summary"; cases.append(("twitter:card summary not large_image", b))
    b = _valid_tags(); b["og:image:width"] = "600"; cases.append(("og:image:width wrong", b))
    b = _valid_tags(); b["og:image:height"] = "315"; cases.append(("og:image:height wrong", b))
    b = _valid_tags(); b["og:image:type"] = "image/jpeg"; cases.append(("og:image:type wrong", b))
    b = _valid_tags(); b["twitter:image"] = "https://big7construction.com/images/jobsite-01.jpg"; cases.append(("twitter:image is 206px placeholder", b))

    failures = [name for name, tags in cases if not assert_og_twitter(tags, "selftest")]
    if failures:
        for name in failures:
            print(f"SELFTEST FAIL: mutation not caught: {name}", file=sys.stderr)
        return 1

    # Canonical/og:url contract selftest — baseline + mutations.
    good_og_url = "https://big7construction.com/commercial-industrial.html"
    good_canonical = ["https://big7construction.com/commercial-industrial.html"]
    if assert_canonical(good_canonical, good_og_url, "selftest-canonical-baseline", must_have_canonical=True):
        print("SELFTEST FAIL: canonical baseline should be valid", file=sys.stderr)
        return 1
    if assert_canonical([], "https://big7construction.com/", "selftest-canonical-404-baseline", must_have_canonical=False):
        print("SELFTEST FAIL: canonical 404-baseline should be valid", file=sys.stderr)
        return 1

    canon_cases: list[tuple[str, list[str], str, bool]] = [
        ("canonical missing on indexable page", [], good_og_url, True),
        ("canonical / og:url mismatch",
         ["https://big7construction.com/"], good_og_url, True),
        ("canonical not https",
         ["http://big7construction.com/commercial-industrial.html"], good_og_url, True),
        ("two canonicals on one page",
         [good_og_url, good_og_url], good_og_url, True),
        ("404 accidentally sprouted a canonical",
         ["https://big7construction.com/"], "https://big7construction.com/", False),
    ]
    canon_failures = [
        name for name, canonicals, og_url, must in canon_cases
        if not assert_canonical(canonicals, og_url, "selftest-canonical", must_have_canonical=must)
    ]
    if canon_failures:
        for name in canon_failures:
            print(f"SELFTEST FAIL: canonical mutation not caught: {name}", file=sys.stderr)
        return 1

    total = len(cases) + len(canon_cases)
    print(
        f"SELFTEST OK: baseline PASS + {len(cases)}/{len(cases)} OG/Twitter mutations caught + "
        f"{len(canon_cases)}/{len(canon_cases)} canonical mutations caught ({total} total)"
    )
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    errors: list[str] = []
    for path in TARGETS:
        if not path.exists():
            errors.append(f"{path.name} not found at {path}")
            continue
        html = path.read_text(encoding="utf-8")
        tags = extract_meta(html)
        errors.extend(assert_og_twitter(tags, path.name))
        canonicals = extract_canonicals(html)
        errors.extend(
            assert_canonical(
                canonicals,
                tags.get("og:url", ""),
                path.name,
                must_have_canonical=(path in TARGETS_WITH_CANONICAL),
            )
        )

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    names = ", ".join(p.name for p in TARGETS)
    print(
        f"OK: {names} carry valid OG + Twitter tags; "
        f"og:image + twitter:image point at branded {BRAND_CARD} (1200x630 image/png); "
        f"canonical <link> agrees with og:url on {len(TARGETS_WITH_CANONICAL)} indexable pages"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
