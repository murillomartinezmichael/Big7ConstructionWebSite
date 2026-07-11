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

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CANONICAL_ORIGIN = "https://big7construction.com"
PROVIDER_NAME = "Big 7 Construction"
PROVIDER_URL = f"{CANONICAL_ORIGIN}/"
PROVIDER_PHONE = "+1-555-700-0007"

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
        if errors:
            for e in errors:
                print(f"FAIL {filename}: {e}")
            failures += 1
        else:
            print(f"PASS {filename}: Service valid ({name})")
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
    print(f"SELFTEST: all {len(mutations)} mutations caught")
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
