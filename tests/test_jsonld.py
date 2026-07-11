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
    "contactPoint",
}

VALID_CONTACT_TYPES = {
    "customer service",
    "sales",
    "technical support",
    "billing support",
    "bill payment",
    "emergency",
    "reservations",
}

# ContactPoint.telephone must agree with the top-level telephone at the
# last-10-digit level so Google's Knowledge Panel + SGE surface one canonical
# number. Same drift class the test_form.py tel:<->JSON-LD lock closes.
_DIGITS_RE = re.compile(r"\D+")

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

# On-page <details class="faq-item"> blocks — the FAQPage schema must expose
# exactly one Question per rendered FAQ. Prevents schema drift when someone
# edits the visible copy without touching the ld+json.
FAQ_DETAILS_RE = re.compile(r'<details\s+class="faq-item"', re.IGNORECASE)


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

    errors.extend(_assert_contact_points(block))

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


def _assert_contact_points(block: dict) -> list[str]:
    errors: list[str] = []
    top_tel_digits = _DIGITS_RE.sub("", block.get("telephone", ""))[-10:]

    cps = block.get("contactPoint")
    if not isinstance(cps, list) or not cps:
        errors.append("contactPoint must be a non-empty list of ContactPoint objects")
        return errors

    seen_types: set[str] = set()
    for i, cp in enumerate(cps):
        if not isinstance(cp, dict):
            errors.append(f"contactPoint[{i}] must be an object, got {type(cp).__name__}")
            continue
        if cp.get("@type") != "ContactPoint":
            errors.append(f'contactPoint[{i}].@type must be "ContactPoint", got {cp.get("@type")!r}')
        ctype = cp.get("contactType")
        if not (isinstance(ctype, str) and ctype.strip()):
            errors.append(f"contactPoint[{i}].contactType must be a non-empty string")
        elif ctype not in VALID_CONTACT_TYPES:
            errors.append(
                f"contactPoint[{i}].contactType {ctype!r} not in Google-recommended set "
                f"{sorted(VALID_CONTACT_TYPES)}"
            )
        else:
            if ctype in seen_types:
                errors.append(f"contactPoint[{i}].contactType {ctype!r} duplicated across entries")
            seen_types.add(ctype)

        tel = cp.get("telephone", "")
        if not re.match(r"^\+?[\d\-\s\(\)]+$", tel):
            errors.append(f"contactPoint[{i}].telephone shape looks wrong: {tel!r}")
        elif top_tel_digits:
            cp_digits = _DIGITS_RE.sub("", tel)[-10:]
            if cp_digits != top_tel_digits:
                errors.append(
                    f"contactPoint[{i}].telephone last-10-digits {cp_digits!r} != top-level "
                    f"telephone last-10-digits {top_tel_digits!r} (drift)"
                )

        langs = cp.get("availableLanguage")
        lang_list = [langs] if isinstance(langs, str) else langs
        if not (isinstance(lang_list, list) and lang_list and all(
            isinstance(l, str) and l.strip() for l in lang_list
        )):
            errors.append(
                f"contactPoint[{i}].availableLanguage must be a non-empty string or list of strings"
            )

        if "email" in cp:
            email = cp["email"]
            if not (isinstance(email, str) and "@" in email and "." in email.split("@")[-1]):
                errors.append(f"contactPoint[{i}].email shape looks wrong: {email!r}")

    return errors


def assert_faq_page(block: dict, on_page_count: int | None = None) -> list[str]:
    errors: list[str] = []

    if block.get("@context") != "https://schema.org":
        errors.append(f'FAQ @context must be "https://schema.org", got {block.get("@context")!r}')

    if block.get("@type") != "FAQPage":
        errors.append(f'FAQ @type must be "FAQPage", got {block.get("@type")!r}')

    entities = block.get("mainEntity")
    if not isinstance(entities, list) or not entities:
        errors.append("FAQ mainEntity must be a non-empty list")
        return errors

    for i, q in enumerate(entities):
        if not isinstance(q, dict):
            errors.append(f"FAQ mainEntity[{i}] must be an object, got {type(q).__name__}")
            continue
        if q.get("@type") != "Question":
            errors.append(f'FAQ mainEntity[{i}].@type must be "Question", got {q.get("@type")!r}')
        name = q.get("name")
        if not (isinstance(name, str) and name.strip()):
            errors.append(f"FAQ mainEntity[{i}].name must be a non-empty string")
        answer = q.get("acceptedAnswer")
        if not isinstance(answer, dict):
            errors.append(f"FAQ mainEntity[{i}].acceptedAnswer must be an object")
            continue
        if answer.get("@type") != "Answer":
            errors.append(f'FAQ mainEntity[{i}].acceptedAnswer.@type must be "Answer", got {answer.get("@type")!r}')
        text = answer.get("text")
        if not (isinstance(text, str) and text.strip()):
            errors.append(f"FAQ mainEntity[{i}].acceptedAnswer.text must be a non-empty string")

    if on_page_count is not None and on_page_count != len(entities):
        errors.append(
            f"FAQ schema/on-page drift: {len(entities)} Question(s) in ld+json vs "
            f"{on_page_count} <details class=\"faq-item\"> in rendered HTML"
        )

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
        "contactPoint": [
            {
                "@type": "ContactPoint",
                "contactType": "customer service",
                "telephone": "+1-555-700-0007",
                "email": "info@big7construction.com",
                "areaServed": "US-GA",
                "availableLanguage": ["English"],
            },
            {
                "@type": "ContactPoint",
                "contactType": "sales",
                "telephone": "+1-555-700-0007",
                "email": "info@big7construction.com",
                "areaServed": "US-GA",
                "availableLanguage": ["English"],
            },
        ],
    }


def _valid_faq_block() -> dict:
    """Minimal-but-valid FAQPage with two Questions — selftest baseline."""
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": "Do you provide fixed-price bids?",
                "acceptedAnswer": {"@type": "Answer", "text": "Yes — fixed bids are the default."},
            },
            {
                "@type": "Question",
                "name": "How does payment work?",
                "acceptedAnswer": {"@type": "Answer", "text": "Milestone-based, not time-based."},
            },
        ],
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
    # contactPoint mutations
    b = _valid_block(); b.pop("contactPoint"); cases.append(("contactPoint missing", b))
    b = _valid_block(); b["contactPoint"] = []; cases.append(("contactPoint empty list", b))
    b = _valid_block(); b["contactPoint"] = "info@big7construction.com"; cases.append(("contactPoint not a list", b))
    b = _valid_block(); b["contactPoint"][0].pop("@type"); cases.append(("contactPoint[0] missing @type", b))
    b = _valid_block(); b["contactPoint"][0]["@type"] = "Person"; cases.append(("contactPoint[0] wrong @type", b))
    b = _valid_block(); b["contactPoint"][0]["contactType"] = "grillmaster"; cases.append(("contactPoint[0] contactType not in Google set", b))
    b = _valid_block(); b["contactPoint"][0].pop("contactType"); cases.append(("contactPoint[0] missing contactType", b))
    b = _valid_block(); b["contactPoint"][0]["telephone"] = "+1-555-123-4567"; cases.append(("contactPoint[0] telephone drifts from top-level", b))
    b = _valid_block(); b["contactPoint"][0]["telephone"] = "call-us"; cases.append(("contactPoint[0] telephone bad shape", b))
    b = _valid_block(); b["contactPoint"][0].pop("availableLanguage"); cases.append(("contactPoint[0] availableLanguage missing", b))
    b = _valid_block(); b["contactPoint"][0]["availableLanguage"] = []; cases.append(("contactPoint[0] availableLanguage empty", b))
    b = _valid_block(); b["contactPoint"][0]["email"] = "not-an-email"; cases.append(("contactPoint[0] email bad shape", b))
    b = _valid_block(); b["contactPoint"][1]["contactType"] = "customer service"; cases.append(("contactPoint duplicate contactType across entries", b))

    failures = [name for name, block in cases if not assert_local_business(block)]
    if failures:
        for name in failures:
            print(f"SELFTEST FAIL: mutation not caught: {name}", file=sys.stderr)
        return 1

    faq_baseline = _valid_faq_block()
    if assert_faq_page(faq_baseline, on_page_count=2):
        print("SELFTEST FAIL: FAQ baseline should be valid", file=sys.stderr)
        return 1

    faq_cases: list[tuple[str, dict, int | None]] = []
    b = _valid_faq_block(); b["@type"] = "Article"; faq_cases.append(("FAQ wrong @type", b, 2))
    b = _valid_faq_block(); b.pop("mainEntity"); faq_cases.append(("FAQ missing mainEntity", b, 2))
    b = _valid_faq_block(); b["mainEntity"] = []; faq_cases.append(("FAQ empty mainEntity", b, 2))
    b = _valid_faq_block(); b["mainEntity"][0].pop("name"); faq_cases.append(("FAQ question missing name", b, 2))
    b = _valid_faq_block(); b["mainEntity"][0]["acceptedAnswer"].pop("text"); faq_cases.append(("FAQ answer missing text", b, 2))
    b = _valid_faq_block(); b["mainEntity"][0]["acceptedAnswer"]["@type"] = "Comment"; faq_cases.append(("FAQ answer wrong @type", b, 2))
    b = _valid_faq_block(); faq_cases.append(("FAQ count drift (2 in schema vs 3 on-page)", b, 3))

    faq_failures = [name for name, block, cnt in faq_cases if not assert_faq_page(block, cnt)]
    if faq_failures:
        for name in faq_failures:
            print(f"SELFTEST FAIL: FAQ mutation not caught: {name}", file=sys.stderr)
        return 1

    print(
        f"SELFTEST OK: LB baseline PASS + {len(cases)}/{len(cases)} LB mutations caught; "
        f"FAQ baseline PASS + {len(faq_cases)}/{len(faq_cases)} FAQ mutations caught"
    )
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
    faq_seen = False
    on_page_faq_count = len(FAQ_DETAILS_RE.findall(html))
    for i, block in enumerate(blocks):
        types = block.get("@type")
        type_set = set(types) if isinstance(types, list) else {types}
        if type_set & LOCAL_BUSINESS_TYPES:
            lb_seen = True
            errors.extend(f"block[{i}]: {e}" for e in assert_local_business(block))
        if "FAQPage" in type_set:
            faq_seen = True
            errors.extend(f"block[{i}]: {e}" for e in assert_faq_page(block, on_page_faq_count))

    if not lb_seen:
        print("FAIL: no LocalBusiness / GeneralContractor JSON-LD block found", file=sys.stderr)
        return 1

    if on_page_faq_count > 0 and not faq_seen:
        print(
            f"FAIL: {on_page_faq_count} on-page <details class=\"faq-item\"> present but no "
            "FAQPage JSON-LD block found",
            file=sys.stderr,
        )
        return 1

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(
        f"OK: {len(blocks)} JSON-LD block(s) parsed, LocalBusiness valid"
        + (f", FAQPage valid ({on_page_faq_count} Q's in sync)" if faq_seen else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
