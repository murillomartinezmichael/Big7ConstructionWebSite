"""
Parent GeneralContractor `hasOfferCatalog` ↔ three-lane IA drift lock.

Why: index.html's LocalBusiness/GeneralContractor JSON-LD carries a
`hasOfferCatalog` field. The site's IA is three lanes
(commercial-industrial / residential-construction / home-repair), and each
lane page carries its own `Service` JSON-LD. If the parent catalog stops
mirroring the three-lane IA — wrong number of divisions, wrong URL,
url→file mismatch, or drift against a lane page's Service.url — the
schema.org graph desyncs from the on-page IA and Google's rich-result
grouping breaks silently.

Locks:
  1. The parent GeneralContractor block on index.html carries an
     `hasOfferCatalog` OfferCatalog with exactly 3 nested OfferCatalogs.
  2. Each nested catalog has a `url` on canonical origin whose path
     matches one of the three lane HTML files on disk.
  3. The three nested catalog URLs equal the `url` field of the Service
     JSON-LD on the corresponding lane page (parent↔lane URL agreement).
  4. Each nested catalog has ≥1 Offer with a Service.name+description.
  5. No duplicate lane URLs, no unknown lane URLs.

Stdlib only (Python 3.11+ — `json` / `re` / `pathlib` / `sys`) so
`python tests/test_offer_catalog.py` runs with zero setup.

Run:
    python tests/test_offer_catalog.py            # golden check
    python tests/test_offer_catalog.py --selftest # mutate baseline N ways, expect each to fail
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CANONICAL_ORIGIN = "https://big7construction.com"

# (lane page filename, expected Service.name on that page)
# Order matches the visible IA (2026-07-17 two-path restructure):
# commercial → residential (home repair folded into residential).
LANES: tuple[tuple[str, str], ...] = (
    ("commercial-industrial.html", "Commercial & Industrial"),
    ("residential-construction.html", "Residential Construction"),
)

LOCAL_BUSINESS_TYPES = {
    "LocalBusiness",
    "GeneralContractor",
    "HomeAndConstructionBusiness",
    "Contractor",
}

SCRIPT_RE = re.compile(
    r'<script\s+type="application/ld\+json">\s*(?P<body>\{.*?\})\s*</script>',
    re.DOTALL | re.IGNORECASE,
)


def find_local_business(html: str) -> dict | None:
    for m in SCRIPT_RE.finditer(html):
        try:
            block = json.loads(m.group("body"))
        except json.JSONDecodeError:
            continue
        if block.get("@type") in LOCAL_BUSINESS_TYPES:
            return block
    return None


def find_service_url(html: str) -> str | None:
    for m in SCRIPT_RE.finditer(html):
        try:
            block = json.loads(m.group("body"))
        except json.JSONDecodeError:
            continue
        if block.get("@type") == "Service":
            url = block.get("url")
            if isinstance(url, str):
                return url
    return None


def assert_catalog(parent: dict, expected_lane_urls: list[str]) -> list[str]:
    """Verify parent.hasOfferCatalog mirrors the three-lane IA.

    `expected_lane_urls` is the list of Service.url values pulled from the
    three lane pages (drift lock — the parent's nested catalog URLs must
    equal these, order-independent).
    """
    errors: list[str] = []

    catalog = parent.get("hasOfferCatalog")
    if not isinstance(catalog, dict):
        errors.append(f"hasOfferCatalog must be an object, got {type(catalog).__name__}")
        return errors

    if catalog.get("@type") != "OfferCatalog":
        errors.append(
            f'hasOfferCatalog.@type must be "OfferCatalog", got {catalog.get("@type")!r}'
        )

    items = catalog.get("itemListElement")
    if not isinstance(items, list):
        errors.append(
            f"hasOfferCatalog.itemListElement must be a list, got {type(items).__name__}"
        )
        return errors

    if len(items) != len(LANES):
        errors.append(
            f"hasOfferCatalog.itemListElement must have exactly {len(LANES)} nested "
            f"OfferCatalogs (two-path IA), got {len(items)}"
        )

    seen_urls: list[str] = []
    for idx, sub in enumerate(items):
        prefix = f"itemListElement[{idx}]"
        if not isinstance(sub, dict):
            errors.append(f"{prefix} must be an object, got {type(sub).__name__}")
            continue
        if sub.get("@type") != "OfferCatalog":
            errors.append(
                f'{prefix}.@type must be "OfferCatalog", got {sub.get("@type")!r}'
            )
        name = sub.get("name")
        if not (isinstance(name, str) and name.strip()):
            errors.append(f"{prefix}.name must be a non-empty string, got {name!r}")

        url = sub.get("url")
        if not (isinstance(url, str) and url.strip()):
            errors.append(f"{prefix}.url must be a non-empty string, got {url!r}")
        else:
            if not url.startswith(CANONICAL_ORIGIN + "/"):
                errors.append(
                    f"{prefix}.url must be on canonical origin "
                    f"{CANONICAL_ORIGIN}/, got {url!r}"
                )
            path_part = url[len(CANONICAL_ORIGIN) + 1:] if url.startswith(CANONICAL_ORIGIN + "/") else ""
            # Clean-URL form (2026-07-19): lane URLs are extensionless
            # (`/commercial-industrial` serves commercial-industrial.html);
            # accept either the literal file or the `.html` sibling.
            if path_part and not (
                (REPO_ROOT / path_part).is_file()
                or (REPO_ROOT / f"{path_part}.html").is_file()
            ):
                errors.append(
                    f"{prefix}.url points at {path_part!r} which is not an on-disk lane file"
                )
            seen_urls.append(url)

        offers = sub.get("itemListElement")
        if not (isinstance(offers, list) and offers):
            errors.append(f"{prefix}.itemListElement must be a non-empty list, got {offers!r}")
        else:
            for oi, offer in enumerate(offers):
                op = f"{prefix}.itemListElement[{oi}]"
                if not isinstance(offer, dict):
                    errors.append(f"{op} must be an object, got {type(offer).__name__}")
                    continue
                if offer.get("@type") != "Offer":
                    errors.append(f'{op}.@type must be "Offer", got {offer.get("@type")!r}')
                svc = offer.get("itemOffered")
                if not isinstance(svc, dict):
                    errors.append(f"{op}.itemOffered must be an object, got {type(svc).__name__}")
                    continue
                if svc.get("@type") != "Service":
                    errors.append(
                        f'{op}.itemOffered.@type must be "Service", got {svc.get("@type")!r}'
                    )
                sname = svc.get("name")
                if not (isinstance(sname, str) and sname.strip()):
                    errors.append(f"{op}.itemOffered.name must be a non-empty string, got {sname!r}")
                sdesc = svc.get("description")
                if not (isinstance(sdesc, str) and len(sdesc.strip()) >= 40):
                    errors.append(
                        f"{op}.itemOffered.description must be a usable snippet (>=40 chars), "
                        f"got {sdesc!r}"
                    )

    if len(seen_urls) != len(set(seen_urls)):
        errors.append(f"nested OfferCatalog urls contain duplicates: {seen_urls}")

    expected_set = set(expected_lane_urls)
    seen_set = set(seen_urls)
    missing = expected_set - seen_set
    if missing:
        errors.append(
            f"parent hasOfferCatalog missing lane url(s): {sorted(missing)} "
            f"(drift vs lane-page Service.url)"
        )
    unknown = seen_set - expected_set
    if unknown:
        errors.append(
            f"parent hasOfferCatalog carries unknown lane url(s): {sorted(unknown)} "
            f"(drift vs lane-page Service.url)"
        )

    return errors


def golden() -> int:
    index_path = REPO_ROOT / "index.html"
    if not index_path.exists():
        print("FAIL index.html: missing")
        return 1

    lane_urls: list[str] = []
    for lane_file, lane_name in LANES:
        lp = REPO_ROOT / lane_file
        if not lp.exists():
            print(f"FAIL {lane_file}: missing")
            return 1
        url = find_service_url(lp.read_text(encoding="utf-8"))
        if not url:
            print(f"FAIL {lane_file}: no Service JSON-LD with a url field found")
            return 1
        lane_urls.append(url)

    parent = find_local_business(index_path.read_text(encoding="utf-8"))
    if parent is None:
        print("FAIL index.html: no LocalBusiness / GeneralContractor JSON-LD block found")
        return 1

    errors = assert_catalog(parent, lane_urls)
    if errors:
        for e in errors:
            print(f"FAIL index.html: {e}")
        return 1

    print(
        f"PASS: hasOfferCatalog carries {len(LANES)} nested OfferCatalogs "
        f"whose urls agree with the three lane pages' Service.url."
    )
    return 0


def _baseline_lane_urls() -> list[str]:
    return [f"{CANONICAL_ORIGIN}/{f}" for f, _ in LANES]


def _baseline() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "GeneralContractor",
        "name": "Big 7 Construction",
        "hasOfferCatalog": {
            "@type": "OfferCatalog",
            "name": "Divisions",
            "itemListElement": [
                {
                    "@type": "OfferCatalog",
                    "name": "Commercial & Industrial",
                    "url": f"{CANONICAL_ORIGIN}/commercial-industrial.html",
                    "itemListElement": [
                        {
                            "@type": "Offer",
                            "itemOffered": {
                                "@type": "Service",
                                "name": "Commercial New Construction",
                                "description": "Ground-up offices, retail, and institutional builds — permit to punch list.",
                            },
                        }
                    ],
                },
                {
                    "@type": "OfferCatalog",
                    "name": "Residential Construction",
                    "url": f"{CANONICAL_ORIGIN}/residential-construction.html",
                    "itemListElement": [
                        {
                            "@type": "Offer",
                            "itemOffered": {
                                "@type": "Service",
                                "name": "Custom Home Builds",
                                "description": "Ground-up residential builds with owner-vision plans and defensible budget.",
                            },
                        }
                    ],
                },
            ],
        },
    }


def selftest() -> int:
    expected_urls = _baseline_lane_urls()

    baseline_errors = assert_catalog(_baseline(), expected_urls)
    if baseline_errors:
        print("SELFTEST FAIL: baseline should PASS but got errors:")
        for e in baseline_errors:
            print(f"  - {e}")
        return 1

    def clone() -> dict:
        return json.loads(json.dumps(_baseline()))

    mutations: list[tuple[str, callable]] = [
        (
            "hasOfferCatalog missing",
            lambda b: b.pop("hasOfferCatalog"),
        ),
        (
            "hasOfferCatalog wrong @type",
            lambda b: b["hasOfferCatalog"].__setitem__("@type", "ItemList"),
        ),
        (
            "wrong division count (one dropped)",
            lambda b: b["hasOfferCatalog"]["itemListElement"].pop(),
        ),
        (
            "extra fourth division",
            lambda b: b["hasOfferCatalog"]["itemListElement"].append(
                {
                    "@type": "OfferCatalog",
                    "name": "Bogus",
                    "url": f"{CANONICAL_ORIGIN}/bogus.html",
                    "itemListElement": [
                        {
                            "@type": "Offer",
                            "itemOffered": {
                                "@type": "Service",
                                "name": "Bogus",
                                "description": "Something long enough to pass length check.",
                            },
                        }
                    ],
                }
            ),
        ),
        (
            "division url wrong origin",
            lambda b: b["hasOfferCatalog"]["itemListElement"][0].__setitem__(
                "url", "https://someone-else.example/commercial-industrial.html"
            ),
        ),
        (
            "division url path off-disk",
            lambda b: b["hasOfferCatalog"]["itemListElement"][0].__setitem__(
                "url", f"{CANONICAL_ORIGIN}/does-not-exist.html"
            ),
        ),
        (
            "division url drift vs lane page",
            lambda b: b["hasOfferCatalog"]["itemListElement"][0].__setitem__(
                "url", f"{CANONICAL_ORIGIN}/index.html"
            ),
        ),
        (
            "duplicate division url",
            lambda b: b["hasOfferCatalog"]["itemListElement"][1].__setitem__(
                "url", b["hasOfferCatalog"]["itemListElement"][0]["url"]
            ),
        ),
        (
            "nested @type wrong",
            lambda b: b["hasOfferCatalog"]["itemListElement"][0].__setitem__("@type", "Thing"),
        ),
        (
            "division name empty",
            lambda b: b["hasOfferCatalog"]["itemListElement"][0].__setitem__("name", ""),
        ),
        (
            "division itemListElement empty",
            lambda b: b["hasOfferCatalog"]["itemListElement"][0].__setitem__("itemListElement", []),
        ),
        (
            "offer @type wrong",
            lambda b: b["hasOfferCatalog"]["itemListElement"][0]["itemListElement"][0].__setitem__(
                "@type", "Something"
            ),
        ),
        (
            "itemOffered @type wrong",
            lambda b: b["hasOfferCatalog"]["itemListElement"][0]["itemListElement"][0][
                "itemOffered"
            ].__setitem__("@type", "Product"),
        ),
        (
            "service name empty",
            lambda b: b["hasOfferCatalog"]["itemListElement"][0]["itemListElement"][0][
                "itemOffered"
            ].__setitem__("name", ""),
        ),
        (
            "service description too short",
            lambda b: b["hasOfferCatalog"]["itemListElement"][0]["itemListElement"][0][
                "itemOffered"
            ].__setitem__("description", "short"),
        ),
    ]

    fails = 0
    for label, mutate in mutations:
        b = clone()
        mutate(b)
        errs = assert_catalog(b, expected_urls)
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
    return golden()


if __name__ == "__main__":
    raise SystemExit(main())
