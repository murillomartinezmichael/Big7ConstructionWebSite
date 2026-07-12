"""
Service JSON-LD contract on the three lane pages.

Why: each lane page (home-repair, commercial-industrial, residential-construction)
carries its own `Service` structured-data block pointing back at the
LocalBusiness on `/`. This makes each lane a rich-result candidate for
lane-specific queries ("home repair atlanta", "commercial gc atlanta",
"custom home builder atlanta") instead of relying on the homepage's
GeneralContractor block alone.

A silent parse break, a missing block, or a `provider` URL drift kills that
signal and no other suite catches it (test_breadcrumbs.py only looks at the
BreadcrumbList block on the same page; test_jsonld.py only runs on index.html).

Stdlib only (Python 3.11+ — `json` / `re` / `pathlib` / `sys`) so
`python tests/test_service_schema.py` runs with zero setup.

Run:
    python tests/test_service_schema.py            # golden check on the three lane files
    python tests/test_service_schema.py --selftest # mutate baseline N ways, expect each to fail
"""
from __future__ import annotations

import html as html_lib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CANONICAL_ORIGIN = "https://big7construction.com"
PROVIDER_NAME = "Big 7 Construction"
PROVIDER_URL = f"{CANONICAL_ORIGIN}/"
PROVIDER_PHONE = "+1-555-700-0007"

# Every visible <span class="service-title">…</span> on a lane page must appear
# as an OfferCatalog.itemListElement.itemOffered.name in that page's Service
# JSON-LD, and vice versa. If the visible copy is edited without touching the
# ld+json (or vice versa), Google surfaces stale sub-services on the local pack
# while the on-page CTA rows point somewhere else. Same drift class the FAQ-count
# sync in tests/test_jsonld.py closes for the homepage.
SERVICE_TITLE_RE = re.compile(
    r'<span\s+class="service-title">(?P<title>[^<]+)</span>',
    re.IGNORECASE,
)

# (file, expected Service name, expected canonical URL)
TARGETS: tuple[tuple[str, str, str], ...] = (
    ("home-repair.html", "Home Repair & Improvements", f"{CANONICAL_ORIGIN}/home-repair.html"),
    ("commercial-industrial.html", "Commercial & Industrial", f"{CANONICAL_ORIGIN}/commercial-industrial.html"),
    ("residential-construction.html", "Residential Construction", f"{CANONICAL_ORIGIN}/residential-construction.html"),
)

SCRIPT_RE = re.compile(
    r'<script\s+type="application/ld\+json">\s*(?P<body>\{.*?\})\s*</script>',
    re.DOTALL | re.IGNORECASE,
)

PROVIDER_LOCAL_BUSINESS_TYPES = {
    "LocalBusiness",
    "GeneralContractor",
    "HomeAndConstructionBusiness",
    "Contractor",
}


def find_service_block(html: str) -> dict | None:
    for m in SCRIPT_RE.finditer(html):
        try:
            block = json.loads(m.group("body"))
        except json.JSONDecodeError:
            continue
        if block.get("@type") == "Service":
            return block
    return None


def assert_service(block: dict, name: str, url: str) -> list[str]:
    errors: list[str] = []

    if block.get("@context") != "https://schema.org":
        errors.append(f'@context must be "https://schema.org", got {block.get("@context")!r}')

    if block.get("@type") != "Service":
        errors.append(f'@type must be "Service", got {block.get("@type")!r}')

    if block.get("name") != name:
        errors.append(f"name must be {name!r}, got {block.get('name')!r}")

    if block.get("url") != url:
        errors.append(f"url must be {url!r}, got {block.get('url')!r}")

    service_type = block.get("serviceType")
    if not (isinstance(service_type, str) and service_type.strip()):
        errors.append(f"serviceType must be a non-empty string, got {service_type!r}")

    description = block.get("description")
    if not (isinstance(description, str) and len(description.strip()) >= 40):
        errors.append(
            f"description must be a non-empty string (>=40 chars for a usable snippet), "
            f"got {description!r}"
        )

    provider = block.get("provider")
    if not isinstance(provider, dict):
        errors.append(f"provider must be an object, got {type(provider).__name__}")
    else:
        ptype = provider.get("@type")
        if ptype not in PROVIDER_LOCAL_BUSINESS_TYPES:
            errors.append(
                f"provider.@type must be a LocalBusiness subtype "
                f"(one of {sorted(PROVIDER_LOCAL_BUSINESS_TYPES)}), got {ptype!r}"
            )
        if provider.get("name") != PROVIDER_NAME:
            errors.append(f"provider.name must be {PROVIDER_NAME!r}, got {provider.get('name')!r}")
        if provider.get("url") != PROVIDER_URL:
            errors.append(f"provider.url must be {PROVIDER_URL!r}, got {provider.get('url')!r}")
        tel = provider.get("telephone", "")
        if not re.match(r"^\+?[\d\-\s\(\)]+$", tel):
            errors.append(f"provider.telephone shape looks wrong: {tel!r}")
        addr = provider.get("address", {})
        if addr.get("@type") != "PostalAddress":
            errors.append(f'provider.address.@type must be "PostalAddress", got {addr.get("@type")!r}')
        for k in ("addressLocality", "addressRegion", "addressCountry"):
            if not addr.get(k):
                errors.append(f"provider.address.{k} missing or empty")

    area = block.get("areaServed")
    if not (isinstance(area, list) and area):
        errors.append(f"areaServed must be a non-empty list, got {area!r}")
    else:
        allowed_types = {"City", "State", "AdministrativeArea", "Place"}
        for i, a in enumerate(area):
            if not isinstance(a, dict):
                errors.append(f"areaServed[{i}] must be an object, got {type(a).__name__}")
                continue
            atype = a.get("@type")
            if atype not in allowed_types:
                errors.append(
                    f"areaServed[{i}].@type must be one of {sorted(allowed_types)}, got {atype!r}"
                )
            if not a.get("name"):
                errors.append(f"areaServed[{i}].name missing or empty")

    errors.extend(_assert_offer_catalog(block))

    return errors


def _assert_offer_catalog(block: dict) -> list[str]:
    """Enforce OfferCatalog shape on the Service block.

    Sync between the OfferCatalog offer names and the on-page visible
    service-title spans is enforced at the file level in assert_service_page —
    this function only validates the JSON-LD internal shape.
    """
    errors: list[str] = []
    catalog = block.get("hasOfferCatalog")
    if not isinstance(catalog, dict):
        errors.append(f"hasOfferCatalog must be an object, got {type(catalog).__name__}")
        return errors
    if catalog.get("@type") != "OfferCatalog":
        errors.append(f'hasOfferCatalog.@type must be "OfferCatalog", got {catalog.get("@type")!r}')
    if not (isinstance(catalog.get("name"), str) and catalog["name"].strip()):
        errors.append("hasOfferCatalog.name must be a non-empty string")

    items = catalog.get("itemListElement")
    if not (isinstance(items, list) and items):
        errors.append("hasOfferCatalog.itemListElement must be a non-empty list of Offer objects")
        return errors

    seen_names: set[str] = set()
    for i, offer in enumerate(items):
        if not isinstance(offer, dict):
            errors.append(f"hasOfferCatalog.itemListElement[{i}] must be an object")
            continue
        if offer.get("@type") != "Offer":
            errors.append(
                f'hasOfferCatalog.itemListElement[{i}].@type must be "Offer", '
                f'got {offer.get("@type")!r}'
            )
        io = offer.get("itemOffered")
        if not isinstance(io, dict):
            errors.append(
                f"hasOfferCatalog.itemListElement[{i}].itemOffered must be an object"
            )
            continue
        if io.get("@type") != "Service":
            errors.append(
                f'hasOfferCatalog.itemListElement[{i}].itemOffered.@type must be "Service", '
                f'got {io.get("@type")!r}'
            )
        name = io.get("name")
        if not (isinstance(name, str) and name.strip()):
            errors.append(
                f"hasOfferCatalog.itemListElement[{i}].itemOffered.name must be a non-empty string"
            )
        elif name in seen_names:
            errors.append(
                f"hasOfferCatalog.itemListElement[{i}].itemOffered.name duplicated: {name!r}"
            )
        else:
            seen_names.add(name)
        url = io.get("url")
        if not (isinstance(url, str) and url.startswith(f"{CANONICAL_ORIGIN}/")):
            errors.append(
                f"hasOfferCatalog.itemListElement[{i}].itemOffered.url must be an absolute URL "
                f"on {CANONICAL_ORIGIN}, got {url!r}"
            )
    return errors


def extract_visible_service_titles(html: str) -> list[str]:
    """Return the visible <span class="service-title"> text on a lane page.

    Titles are HTML-unescaped so `&amp;` / `&middot;` round-trip against the
    JSON-LD offer names cleanly.
    """
    return [html_lib.unescape(m.group("title")).strip() for m in SERVICE_TITLE_RE.finditer(html)]


def assert_visible_offer_sync(html: str, block: dict) -> list[str]:
    """Lock schema/on-page drift: visible service titles ↔ OfferCatalog offer names."""
    errors: list[str] = []
    visible = extract_visible_service_titles(html)
    catalog = block.get("hasOfferCatalog", {})
    items = catalog.get("itemListElement", []) if isinstance(catalog, dict) else []
    schema_names = [
        io["name"]
        for offer in items
        if isinstance(offer, dict)
        and isinstance((io := offer.get("itemOffered")), dict)
        and isinstance(io.get("name"), str)
    ]

    if not visible:
        errors.append(
            'no <span class="service-title"> spans found in page HTML — the '
            "visible sub-service rows disappeared or the class name drifted"
        )
        return errors

    missing_from_schema = [t for t in visible if t not in schema_names]
    if missing_from_schema:
        errors.append(
            f"visible service-title(s) not in Service.hasOfferCatalog offers: "
            f"{missing_from_schema!r} — schema drift, Google will surface a stale "
            f"sub-service list"
        )
    orphan_in_schema = [n for n in schema_names if n not in visible]
    if orphan_in_schema:
        errors.append(
            f"Service.hasOfferCatalog offer name(s) not visible on page: "
            f"{orphan_in_schema!r} — the on-page sub-service row was removed or "
            f"renamed but the ld+json still advertises it"
        )
    if len(visible) != len(schema_names):
        errors.append(
            f"visible sub-service count ({len(visible)}) != OfferCatalog offer count "
            f"({len(schema_names)}) — count drift"
        )
    return errors


def golden() -> int:
    failures = 0
    for filename, name, url in TARGETS:
        path = REPO_ROOT / filename
        if not path.exists():
            print(f"FAIL {filename}: missing")
            failures += 1
            continue
        html = path.read_text(encoding="utf-8")
        block = find_service_block(html)
        if block is None:
            print(f"FAIL {filename}: no Service JSON-LD block found")
            failures += 1
            continue
        errors = assert_service(block, name, url)
        errors.extend(assert_visible_offer_sync(html, block))
        if errors:
            for e in errors:
                print(f"FAIL {filename}: {e}")
            failures += 1
        else:
            offer_count = len(block.get("hasOfferCatalog", {}).get("itemListElement", []))
            print(f"PASS {filename}: Service valid ({name}, {offer_count} offer(s) sync'd to page)")
    return failures


def _baseline() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": "Home Repair & Improvements",
        "serviceType": "Home Repair and Renovation",
        "description": "Homeowner repair, replace, and improvement work in Metro Atlanta. Licensed, bonded, insured.",
        "url": f"{CANONICAL_ORIGIN}/home-repair.html",
        "provider": {
            "@type": "GeneralContractor",
            "name": PROVIDER_NAME,
            "url": PROVIDER_URL,
            "telephone": PROVIDER_PHONE,
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Atlanta",
                "addressRegion": "GA",
                "addressCountry": "US",
            },
        },
        "areaServed": [
            {"@type": "City", "name": "Atlanta"},
            {"@type": "State", "name": "Georgia"},
        ],
        "hasOfferCatalog": {
            "@type": "OfferCatalog",
            "name": "Home Repair & Improvements — services",
            "itemListElement": [
                {
                    "@type": "Offer",
                    "itemOffered": {
                        "@type": "Service",
                        "name": "Structural repair",
                        "url": f"{CANONICAL_ORIGIN}/?intent=service:structural-repair&src=home-repair-lane#contact",
                    },
                },
                {
                    "@type": "Offer",
                    "itemOffered": {
                        "@type": "Service",
                        "name": "Interior remodel · whole-room and above",
                        "url": f"{CANONICAL_ORIGIN}/?intent=service:custom-home&src=home-repair-lane#contact",
                    },
                },
            ],
        },
    }


def selftest() -> int:
    base_name = "Home Repair & Improvements"
    base_url = f"{CANONICAL_ORIGIN}/home-repair.html"

    baseline_errors = assert_service(_baseline(), base_name, base_url)
    if baseline_errors:
        print("SELFTEST FAIL: baseline should PASS but got errors:")
        for e in baseline_errors:
            print(f"  - {e}")
        return 1

    def clone() -> dict:
        return json.loads(json.dumps(_baseline()))

    mutations: list[tuple[str, callable]] = [
        ("context wrong", lambda b: b.__setitem__("@context", "http://schema.org")),
        ("type wrong", lambda b: b.__setitem__("@type", "Product")),
        ("name drift", lambda b: b.__setitem__("name", "Home Repair")),
        ("url wrong origin", lambda b: b.__setitem__("url", "https://example.com/home-repair.html")),
        ("serviceType missing", lambda b: b.pop("serviceType")),
        ("description too short", lambda b: b.__setitem__("description", "Yes.")),
        ("provider missing", lambda b: b.pop("provider")),
        ("provider wrong type", lambda b: b["provider"].__setitem__("@type", "Person")),
        ("provider name drift", lambda b: b["provider"].__setitem__("name", "Someone Else Construction")),
        ("provider url drift", lambda b: b["provider"].__setitem__("url", "https://someone-else.example/")),
        ("provider telephone garbage", lambda b: b["provider"].__setitem__("telephone", "call us")),
        ("provider address missing region", lambda b: b["provider"]["address"].pop("addressRegion")),
        ("provider address type wrong", lambda b: b["provider"]["address"].__setitem__("@type", "Text")),
        ("areaServed missing", lambda b: b.pop("areaServed")),
        ("areaServed empty", lambda b: b.__setitem__("areaServed", [])),
        ("areaServed item wrong type", lambda b: b["areaServed"][0].__setitem__("@type", "Widget")),
        ("areaServed item missing name", lambda b: b["areaServed"][0].pop("name")),
        ("hasOfferCatalog missing", lambda b: b.pop("hasOfferCatalog")),
        ("hasOfferCatalog wrong type", lambda b: b["hasOfferCatalog"].__setitem__("@type", "ItemList")),
        ("hasOfferCatalog empty offers", lambda b: b["hasOfferCatalog"].__setitem__("itemListElement", [])),
        ("offer wrong @type", lambda b: b["hasOfferCatalog"]["itemListElement"][0].__setitem__("@type", "Product")),
        ("offer itemOffered missing", lambda b: b["hasOfferCatalog"]["itemListElement"][0].pop("itemOffered")),
        ("offer itemOffered wrong @type", lambda b: b["hasOfferCatalog"]["itemListElement"][0]["itemOffered"].__setitem__("@type", "Thing")),
        ("offer itemOffered.name empty", lambda b: b["hasOfferCatalog"]["itemListElement"][0]["itemOffered"].__setitem__("name", "")),
        ("offer itemOffered.url wrong origin", lambda b: b["hasOfferCatalog"]["itemListElement"][0]["itemOffered"].__setitem__("url", "https://example.com/x")),
        ("offer itemOffered.name duplicated across entries", lambda b: b["hasOfferCatalog"]["itemListElement"][1]["itemOffered"].__setitem__("name", "Structural repair")),
    ]

    fails = 0
    for label, mutate in mutations:
        b = clone()
        mutate(b)
        errs = assert_service(b, base_name, base_url)
        if not errs:
            print(f"SELFTEST FAIL: mutation {label!r} was NOT caught")
            fails += 1
        else:
            print(f"SELFTEST OK  ({label}) caught: {errs[0]}")

    if fails:
        print(f"SELFTEST: {fails} mutation(s) not caught")
        return 1

    # Visible-title ↔ OfferCatalog sync mutations. Baseline is a minimal HTML
    # snippet whose two visible service titles exactly match the two offer
    # names in _baseline()'s hasOfferCatalog.
    good_html = (
        '<span class="service-title">Structural repair</span>\n'
        '<span class="service-title">Interior remodel &middot; whole-room and above</span>\n'
    )
    sync_baseline_errs = assert_visible_offer_sync(good_html, _baseline())
    if sync_baseline_errs:
        print("SELFTEST FAIL: sync baseline should PASS but got errors:")
        for e in sync_baseline_errs:
            print(f"  - {e}")
        return 1

    sync_cases: list[tuple[str, str, dict, str]] = [
        (
            "visible title renamed but schema stale",
            good_html.replace("Structural repair", "Structural repair &amp; underpinning"),
            _baseline(),
            "not in Service.hasOfferCatalog offers",
        ),
        (
            "schema advertises offer the page doesn't show",
            good_html,
            (lambda b: (b["hasOfferCatalog"]["itemListElement"].append({
                "@type": "Offer",
                "itemOffered": {"@type": "Service", "name": "Ghost service", "url": f"{CANONICAL_ORIGIN}/x"},
            }), b)[1])(json.loads(json.dumps(_baseline()))),
            "not visible on page",
        ),
        (
            "no visible service-title spans at all",
            "<p>lane page with no CTA rows</p>",
            _baseline(),
            "no <span class=\"service-title\"> spans found",
        ),
    ]

    sync_fails = 0
    for label, html, block, needle in sync_cases:
        errs = assert_visible_offer_sync(html, block)
        if not errs:
            print(f"SELFTEST FAIL: sync mutation {label!r} was NOT caught")
            sync_fails += 1
        elif not any(needle in e for e in errs):
            print(f"SELFTEST FAIL: sync mutation {label!r} caught but wrong error: {errs}")
            sync_fails += 1
        else:
            print(f"SELFTEST OK  ({label}) caught: {errs[0]}")

    if sync_fails:
        print(f"SELFTEST: {sync_fails} sync mutation(s) not caught")
        return 1

    print(f"SELFTEST: all {len(mutations)} schema + {len(sync_cases)} sync mutations caught")
    return 0


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return selftest()
    fails = golden()
    if fails:
        print(f"FAIL: {fails} target(s) with errors")
        return 1
    print(f"PASS: all {len(TARGETS)} lane page(s) carry a valid Service JSON-LD block")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
