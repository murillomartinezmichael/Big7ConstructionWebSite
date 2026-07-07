"""
JSON-LD structured-data smoke test.

Why: the `application/ld+json` block in index.html drives Google's local-pack
candidacy — a silent parse break kills a client-facing money signal. Stdlib
only so any Python 3.11+ machine can run `python tests/test_jsonld.py` with
zero setup.

Runs on both index.html (GeneralContractor / LocalBusiness) and 404.html
(no JSON-LD expected — the test just tolerates absence).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "index.html"

SCRIPT_RE = re.compile(
    r'<script type="application/ld\+json">\s*(?P<body>\{.*?\})\s*</script>',
    re.DOTALL,
)

REQUIRED_TOP = {
    "@context",
    "@type",
    "name",
    "description",
    "url",
    "telephone",
    "address",
    "geo",
    "areaServed",
    "priceRange",
    "openingHoursSpecification",
    "hasOfferCatalog",
    "image",
    "logo",
}

# Google Rich Results guidance: LocalBusiness images should be ≥1200 px wide.
# We only assert dimensions when logo is an ImageObject (URL-only form is
# tolerated for back-compat, but the branded og-card path IS an ImageObject).
LOGO_MIN_WIDTH = 112  # Google's absolute minimum for organization logo

LOCAL_BUSINESS_TYPES = {
    "LocalBusiness",
    "GeneralContractor",
    "HomeAndConstructionBusiness",
    "Contractor",
}


def extract_blocks(html: str) -> list[dict]:
    return [json.loads(m.group("body")) for m in SCRIPT_RE.finditer(html)]


def assert_local_business(block: dict) -> list[str]:
    errors: list[str] = []

    if block.get("@context") != "https://schema.org":
        errors.append(f'@context must be "https://schema.org", got {block.get("@context")!r}')

    types = block.get("@type")
    type_set = set(types) if isinstance(types, list) else {types}
    if not type_set & LOCAL_BUSINESS_TYPES:
        errors.append(f"@type must include a LocalBusiness subtype, got {types!r}")

    missing = REQUIRED_TOP - set(block.keys())
    if missing:
        errors.append(f"missing required fields: {sorted(missing)}")

    addr = block.get("address", {})
    if addr.get("@type") != "PostalAddress":
        errors.append(f'address.@type must be "PostalAddress", got {addr.get("@type")!r}')
    for k in ("addressLocality", "addressRegion", "addressCountry"):
        if not addr.get(k):
            errors.append(f"address.{k} missing or empty")

    geo = block.get("geo", {})
    if geo.get("@type") != "GeoCoordinates":
        errors.append(f'geo.@type must be "GeoCoordinates", got {geo.get("@type")!r}')
    lat, lon = geo.get("latitude"), geo.get("longitude")
    if not (isinstance(lat, (int, float)) and -90 <= lat <= 90):
        errors.append(f"geo.latitude out of range or missing: {lat!r}")
    if not (isinstance(lon, (int, float)) and -180 <= lon <= 180):
        errors.append(f"geo.longitude out of range or missing: {lon!r}")

    hours = block.get("openingHoursSpecification", [])
    if not isinstance(hours, list) or not hours:
        errors.append("openingHoursSpecification must be a non-empty list")
    else:
        for i, h in enumerate(hours):
            if h.get("@type") != "OpeningHoursSpecification":
                errors.append(f'openingHoursSpecification[{i}].@type wrong: {h.get("@type")!r}')

    catalog = block.get("hasOfferCatalog", {})
    if catalog.get("@type") != "OfferCatalog":
        errors.append(f'hasOfferCatalog.@type must be "OfferCatalog", got {catalog.get("@type")!r}')
    inner = catalog.get("itemListElement", [])
    if not inner:
        errors.append("hasOfferCatalog.itemListElement is empty")

    tel = block.get("telephone", "")
    if not re.match(r"^\+?[\d\-\s\(\)]+$", tel):
        errors.append(f"telephone shape looks wrong: {tel!r}")

    image = block.get("image")
    image_urls = [image] if isinstance(image, str) else (image if isinstance(image, list) else [])
    if not image_urls:
        errors.append("image must be a non-empty https URL or list of URLs")
    else:
        for i, u in enumerate(image_urls):
            if not (isinstance(u, str) and u.startswith("https://")):
                errors.append(f"image[{i}] must be an absolute https URL, got {u!r}")

    logo = block.get("logo")
    if isinstance(logo, str):
        if not logo.startswith("https://"):
            errors.append(f"logo (string form) must be absolute https, got {logo!r}")
    elif isinstance(logo, dict):
        if logo.get("@type") != "ImageObject":
            errors.append(f'logo.@type must be "ImageObject", got {logo.get("@type")!r}')
        url = logo.get("url") or logo.get("contentUrl")
        if not (isinstance(url, str) and url.startswith("https://")):
            errors.append(f"logo.url/contentUrl must be absolute https, got {url!r}")
        w, h = logo.get("width"), logo.get("height")
        if not (isinstance(w, int) and w >= LOGO_MIN_WIDTH):
            errors.append(f"logo.width must be int ≥ {LOGO_MIN_WIDTH}, got {w!r}")
        if not (isinstance(h, int) and h > 0):
            errors.append(f"logo.height must be positive int, got {h!r}")
    else:
        errors.append(f"logo must be a URL string or ImageObject, got {type(logo).__name__}")

    return errors


def _valid_block() -> dict:
    """Minimal-but-valid LocalBusiness block used as the selftest baseline."""
    return {
        "@context": "https://schema.org",
        "@type": "GeneralContractor",
        "name": "Big 7 Construction",
        "description": "Metro Atlanta general contractor.",
        "url": "https://big7construction.com",
        "telephone": "+1-555-700-0007",
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Atlanta",
            "addressRegion": "GA",
            "addressCountry": "US",
        },
        "geo": {"@type": "GeoCoordinates", "latitude": 33.749, "longitude": -84.388},
        "areaServed": [{"@type": "City", "name": "Atlanta"}],
        "priceRange": "$$-$$$$",
        "openingHoursSpecification": [{"@type": "OpeningHoursSpecification"}],
        "hasOfferCatalog": {"@type": "OfferCatalog", "itemListElement": [{}]},
        "image": ["https://big7construction.com/images/og-card.png"],
        "logo": {
            "@type": "ImageObject",
            "url": "https://big7construction.com/images/og-card.png",
            "width": 1200,
            "height": 630,
        },
    }


def selftest() -> int:
    """Mutate the valid block into known-broken shapes; every mutation must FAIL."""
    baseline = _valid_block()
    if assert_local_business(baseline):
        print("SELFTEST FAIL: baseline block should be valid", file=sys.stderr)
        return 1

    cases: list[tuple[str, dict]] = []
    # image mutations
    b = _valid_block(); b.pop("image"); cases.append(("image missing", b))
    b = _valid_block(); b["image"] = []; cases.append(("image empty list", b))
    b = _valid_block(); b["image"] = ["http://insecure.example/img.png"]; cases.append(("image not https", b))
    b = _valid_block(); b["image"] = [42]; cases.append(("image non-string", b))
    # logo mutations
    b = _valid_block(); b.pop("logo"); cases.append(("logo missing", b))
    b = _valid_block(); b["logo"] = "http://insecure.example/logo.png"; cases.append(("logo string not https", b))
    b = _valid_block(); b["logo"] = {"url": "https://x/y.png", "width": 1200, "height": 630}; cases.append(("logo dict missing @type", b))
    b = _valid_block(); b["logo"] = {"@type": "ImageObject", "url": "https://x/y.png", "width": 50, "height": 50}; cases.append(("logo width below min", b))
    b = _valid_block(); b["logo"] = {"@type": "ImageObject", "url": "https://x/y.png", "width": 1200}; cases.append(("logo missing height", b))
    b = _valid_block(); b["logo"] = 123; cases.append(("logo wrong type", b))

    failures = [name for name, block in cases if not assert_local_business(block)]
    if failures:
        for name in failures:
            print(f"SELFTEST FAIL: mutation not caught: {name}", file=sys.stderr)
        return 1

    print(f"SELFTEST OK: baseline PASS + {len(cases)}/{len(cases)} mutations caught")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    if not INDEX.exists():
        print(f"FAIL: {INDEX} not found", file=sys.stderr)
        return 1

    html = INDEX.read_text(encoding="utf-8")
    blocks = extract_blocks(html)
    if not blocks:
        print("FAIL: no application/ld+json block found in index.html", file=sys.stderr)
        return 1

    errors: list[str] = []
    lb_seen = False
    for i, block in enumerate(blocks):
        types = block.get("@type")
        type_set = set(types) if isinstance(types, list) else {types}
        if type_set & LOCAL_BUSINESS_TYPES:
            lb_seen = True
            errors.extend(f"block[{i}]: {e}" for e in assert_local_business(block))

    if not lb_seen:
        print("FAIL: no LocalBusiness / GeneralContractor JSON-LD block found", file=sys.stderr)
        return 1

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(f"OK: {len(blocks)} JSON-LD block(s) parsed, LocalBusiness schema valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
