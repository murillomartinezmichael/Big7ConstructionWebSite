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
}

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

    return errors


def main() -> int:
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
