"""
BreadcrumbList JSON-LD contract on the three lane pages.

Why: each lane page ships a BreadcrumbList structured-data block so Google
renders "Home > <Lane>" in the SERP snippet instead of a raw URL — the SERP
rich-result CTR bump is the money signal. A silent parse break, a missing
lane, or a URL drift (item -> wrong origin) all silently kill it and no
other suite catches it.

Stdlib only (Python 3.11+ — `json` / `re` / `pathlib` / `sys`) so
`python tests/test_breadcrumbs.py` runs with zero setup.

Run:
    python tests/test_breadcrumbs.py            # golden check on the three real files
    python tests/test_breadcrumbs.py --selftest # mutate baseline N ways, expect each to fail
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CANONICAL_ORIGIN = "https://big7construction.com"

# (file, expected lane name at position 2, expected canonical URL)
TARGETS: tuple[tuple[str, str, str], ...] = (
    ("commercial-industrial.html", "Commercial & Industrial", f"{CANONICAL_ORIGIN}/commercial-industrial.html"),
    ("residential-construction.html", "Residential Construction", f"{CANONICAL_ORIGIN}/residential-construction.html"),
)

SCRIPT_RE = re.compile(
    r'<script\s+type="application/ld\+json">\s*(?P<body>\{.*?\})\s*</script>',
    re.DOTALL | re.IGNORECASE,
)


def find_breadcrumb_block(html: str) -> dict | None:
    for m in SCRIPT_RE.finditer(html):
        try:
            block = json.loads(m.group("body"))
        except json.JSONDecodeError:
            continue
        if block.get("@type") == "BreadcrumbList":
            return block
    return None


def assert_breadcrumb(block: dict, lane_name: str, lane_url: str) -> list[str]:
    errors: list[str] = []

    if block.get("@context") != "https://schema.org":
        errors.append(f'@context must be "https://schema.org", got {block.get("@context")!r}')

    if block.get("@type") != "BreadcrumbList":
        errors.append(f'@type must be "BreadcrumbList", got {block.get("@type")!r}')

    items = block.get("itemListElement")
    if not isinstance(items, list) or len(items) < 2:
        errors.append(f"itemListElement must be a list of >= 2 items, got {items!r}")
        return errors

    # position 1 == Home @ canonical origin root
    home = items[0]
    if home.get("@type") != "ListItem":
        errors.append(f"itemListElement[0] @type must be ListItem, got {home.get('@type')!r}")
    if home.get("position") != 1:
        errors.append(f"itemListElement[0] position must be 1, got {home.get('position')!r}")
    if home.get("name") != "Home":
        errors.append(f'itemListElement[0] name must be "Home", got {home.get("name")!r}')
    if home.get("item") != f"{CANONICAL_ORIGIN}/":
        errors.append(f'itemListElement[0] item must be "{CANONICAL_ORIGIN}/", got {home.get("item")!r}')

    # position 2 == the lane itself
    leaf = items[1]
    if leaf.get("@type") != "ListItem":
        errors.append(f"itemListElement[1] @type must be ListItem, got {leaf.get('@type')!r}")
    if leaf.get("position") != 2:
        errors.append(f"itemListElement[1] position must be 2, got {leaf.get('position')!r}")
    if leaf.get("name") != lane_name:
        errors.append(f"itemListElement[1] name must be {lane_name!r}, got {leaf.get('name')!r}")
    if leaf.get("item") != lane_url:
        errors.append(f"itemListElement[1] item must be {lane_url!r}, got {leaf.get('item')!r}")

    return errors


def golden() -> int:
    failures = 0
    for filename, lane_name, lane_url in TARGETS:
        path = REPO_ROOT / filename
        if not path.exists():
            print(f"FAIL {filename}: missing")
            failures += 1
            continue
        html = path.read_text(encoding="utf-8")
        block = find_breadcrumb_block(html)
        if block is None:
            print(f"FAIL {filename}: no BreadcrumbList JSON-LD block found")
            failures += 1
            continue
        errors = assert_breadcrumb(block, lane_name, lane_url)
        if errors:
            for e in errors:
                print(f"FAIL {filename}: {e}")
            failures += 1
        else:
            print(f"PASS {filename}: BreadcrumbList valid ({lane_name})")
    return failures


BASELINE = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{CANONICAL_ORIGIN}/"},
        {"@type": "ListItem", "position": 2, "name": "Home Repair & Improvements", "item": f"{CANONICAL_ORIGIN}/home-repair.html"},
    ],
}


def selftest() -> int:
    baseline_errors = assert_breadcrumb(BASELINE, "Home Repair & Improvements", f"{CANONICAL_ORIGIN}/home-repair.html")
    if baseline_errors:
        print("SELFTEST FAIL: baseline should PASS but got errors:")
        for e in baseline_errors:
            print(f"  - {e}")
        return 1

    def clone() -> dict:
        return json.loads(json.dumps(BASELINE))

    mutations: list[tuple[str, callable]] = [
        ("context wrong", lambda b: b.__setitem__("@context", "http://schema.org")),
        ("type wrong", lambda b: b.__setitem__("@type", "ItemList")),
        ("itemListElement missing", lambda b: b.pop("itemListElement")),
        ("itemListElement empty", lambda b: b.__setitem__("itemListElement", [])),
        ("home position wrong", lambda b: b["itemListElement"][0].__setitem__("position", 2)),
        ("home name renamed", lambda b: b["itemListElement"][0].__setitem__("name", "Root")),
        ("home item wrong origin", lambda b: b["itemListElement"][0].__setitem__("item", "https://example.com/")),
        ("leaf position wrong", lambda b: b["itemListElement"][1].__setitem__("position", 3)),
        ("leaf name drift", lambda b: b["itemListElement"][1].__setitem__("name", "Home Repair")),
        ("leaf item url drift", lambda b: b["itemListElement"][1].__setitem__("item", f"{CANONICAL_ORIGIN}/home-repair")),
        ("leaf ListItem type wrong", lambda b: b["itemListElement"][1].__setitem__("@type", "Thing")),
    ]

    fails = 0
    for label, mutate in mutations:
        b = clone()
        mutate(b)
        errs = assert_breadcrumb(b, "Home Repair & Improvements", f"{CANONICAL_ORIGIN}/home-repair.html")
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
    print(f"PASS: all {len(TARGETS)} lane page(s) carry a valid BreadcrumbList")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
