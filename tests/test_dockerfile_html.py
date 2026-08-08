"""
Dockerfile-vs-repo drift lock on top-level HTML pages.

Why: this is the deferred Rung II PROVE ticket from tick 17. In that tick,
`accessibility.html` had existed in the repo for weeks (LAW 11 mandate) but
its `COPY` line was never added to the Dockerfile — the file shipped nowhere
because nginx only serves what was baked into the container image. Every
other smoke test in tests/ reads files directly from disk and passes; the
deploy step itself is not tested.

This test walks BOTH surfaces and locks them together:

  1. Every `*.html` at repo root is COPY'd into `/usr/share/nginx/html/` in
     the Dockerfile. If a new lane page is added and the COPY line forgotten,
     the file never leaves the repo — this test fires.

  2. Every `COPY *.html` line in the Dockerfile points at a file that
     actually exists at repo root. If a page is renamed or deleted and the
     COPY line orphaned, `docker build` fails at deploy — this test catches
     it locally before it hits Railway.

  3. Every COPY target is `/usr/share/nginx/html/<same-basename>.html`. A
     drift where a page ends up in a wrong container path silently 404s
     under nginx — this test catches the mapping typo.

Stdlib only (Python 3.11+ — `re` / `pathlib` / `sys`) so
`python tests/test_dockerfile_html.py` runs with zero setup.

Run:
    python tests/test_dockerfile_html.py            # golden: repo vs Dockerfile
    python tests/test_dockerfile_html.py --selftest # mutate baseline N ways, expect each to fail
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = REPO_ROOT / "Dockerfile"

NGINX_HTML_DIR = "/usr/share/nginx/html"

# `COPY <src.html> <dst>` with arbitrary whitespace between the two args.
# Only match single-source COPYs where the source ends in `.html` — that's
# what we care about; the `COPY images/ ...` and `COPY nginx.conf ...` lines
# are separate concerns owned by other tests.
COPY_HTML_RE = re.compile(
    r"^\s*COPY\s+(?P<src>\S+\.html)\s+(?P<dst>\S+)\s*$",
    re.MULTILINE,
)


def parse_dockerfile_copies(dockerfile_text: str) -> list[tuple[str, str]]:
    """Returns [(src, dst), ...] for every COPY <src.html> <dst> line."""
    return [(m.group("src"), m.group("dst")) for m in COPY_HTML_RE.finditer(dockerfile_text)]


def list_root_html(repo_root: Path) -> list[str]:
    """Return sorted list of `*.html` basenames at repo root (non-recursive)."""
    return sorted(p.name for p in repo_root.iterdir() if p.is_file() and p.suffix == ".html")


def check_drift(root_html: list[str], copies: list[tuple[str, str]]) -> list[str]:
    errors: list[str] = []

    copied_srcs = [src for src, _ in copies]
    copied_set = set(copied_srcs)
    root_set = set(root_html)

    # 1. Every root .html file must be COPY'd in the Dockerfile.
    for name in root_html:
        if name not in copied_set:
            errors.append(
                f"{name} exists at repo root but has no `COPY {name} ...` line "
                f"in Dockerfile (would ship as 404 on Railway — tick-17 class regression)"
            )

    # 2. Every Dockerfile COPY source must exist at repo root.
    for src in copied_srcs:
        if src not in root_set:
            errors.append(
                f"Dockerfile has `COPY {src} ...` but {src} does not exist at repo root "
                f"(orphaned COPY — `docker build` will fail on deploy)"
            )

    # 3. Every COPY must target /usr/share/nginx/html/<same basename>.
    for src, dst in copies:
        if src not in root_set:
            # Already reported above; don't double-report the destination.
            continue
        expected = f"{NGINX_HTML_DIR}/{src}"
        if dst != expected:
            errors.append(
                f"Dockerfile `COPY {src} {dst}` target must be {expected!r} "
                f"(nginx serves from {NGINX_HTML_DIR}/; typo silently 404s)"
            )

    # 4. No COPY-line duplicates for the same source (would confuse a future
    # edit — which line is the source of truth?).
    seen: dict[str, int] = {}
    for src in copied_srcs:
        seen[src] = seen.get(src, 0) + 1
    for src, count in seen.items():
        if count > 1:
            errors.append(
                f"Dockerfile has {count} `COPY {src} ...` lines (must be exactly 1; "
                f"duplicates are a merge-conflict smell)"
            )

    return errors


def golden() -> int:
    if not DOCKERFILE.exists():
        print(f"FAIL: Dockerfile not found at {DOCKERFILE}")
        return 1

    dockerfile_text = DOCKERFILE.read_text(encoding="utf-8")
    copies = parse_dockerfile_copies(dockerfile_text)
    root_html = list_root_html(REPO_ROOT)

    if not root_html:
        print("FAIL: no *.html files at repo root — sanity check tripped")
        return 1
    if not copies:
        print("FAIL: Dockerfile has zero `COPY <file>.html <dst>` lines")
        return 1

    errors = check_drift(root_html, copies)
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1

    print(
        f"PASS: {len(root_html)} root *.html file(s) all present in Dockerfile "
        f"COPY chain -> {NGINX_HTML_DIR}/"
    )
    return 0


# ---------------------------------------------------------------------------
# Selftest: exercise check_drift() with a synthetic baseline + known-broken
# mutations. No filesystem writes needed — check_drift is pure over its two
# list arguments.
# ---------------------------------------------------------------------------

BASELINE_ROOT_HTML: list[str] = [
    "index.html",
    "404.html",
    "accessibility.html",
    "commercial-industrial.html",
    "residential-construction.html",
]

BASELINE_COPIES: list[tuple[str, str]] = [
    (name, f"{NGINX_HTML_DIR}/{name}") for name in BASELINE_ROOT_HTML
]


def selftest() -> int:
    baseline_errors = check_drift(list(BASELINE_ROOT_HTML), list(BASELINE_COPIES))
    if baseline_errors:
        print("SELFTEST FAIL: baseline should PASS but got errors:")
        for e in baseline_errors:
            print(f"  - {e}")
        return 1

    mutations: list[tuple[str, list[str], list[tuple[str, str]], str]] = [
        # (label, mutated_root_html, mutated_copies, substring the failure must contain)
        (
            "root html not in Dockerfile (tick-17 regression class)",
            BASELINE_ROOT_HTML + ["new-lane.html"],
            list(BASELINE_COPIES),
            "new-lane.html exists at repo root but has no `COPY",
        ),
        (
            "Dockerfile COPY orphaned (deleted file)",
            [n for n in BASELINE_ROOT_HTML if n != "accessibility.html"],
            list(BASELINE_COPIES),
            "accessibility.html does not exist at repo root",
        ),
        (
            "COPY target directory drift (wrong nginx path)",
            list(BASELINE_ROOT_HTML),
            [
                (n, ("/wrong/path/" + n) if n == "index.html" else f"{NGINX_HTML_DIR}/{n}")
                for n in BASELINE_ROOT_HTML
            ],
            "nginx serves from",
        ),
        (
            "COPY target basename drift (typo in dest filename)",
            list(BASELINE_ROOT_HTML),
            [
                (n, f"{NGINX_HTML_DIR}/index-old.html" if n == "index.html" else f"{NGINX_HTML_DIR}/{n}")
                for n in BASELINE_ROOT_HTML
            ],
            "must be",
        ),
        (
            "duplicate COPY for same source (merge-conflict smell)",
            list(BASELINE_ROOT_HTML),
            list(BASELINE_COPIES) + [("index.html", f"{NGINX_HTML_DIR}/index.html")],
            "must be exactly 1",
        ),
    ]

    fails = 0
    for label, mroot, mcopies, must_contain in mutations:
        errs = check_drift(mroot, mcopies)
        if not errs:
            print(f"SELFTEST FAIL: mutation {label!r} was NOT caught")
            fails += 1
            continue
        if not any(must_contain in e for e in errs):
            print(
                f"SELFTEST FAIL: mutation {label!r} caught the wrong thing — "
                f"expected substring {must_contain!r}, got {errs!r}"
            )
            fails += 1
            continue
        print(f"SELFTEST OK  ({label}) caught: {errs[0]}")

    if fails:
        print(f"SELFTEST: {fails} mutation(s) not caught")
        return 1

    # Also lock the COPY_HTML_RE regex itself against a couple of realistic
    # Dockerfile snippets so a future edit to the regex doesn't silently make
    # every assertion vacuous.
    good_snippet = (
        "FROM nginx:alpine\n"
        "COPY index.html         /usr/share/nginx/html/index.html\n"
        "COPY 404.html           /usr/share/nginx/html/404.html\n"
        "COPY nginx.conf /etc/nginx/conf.d/default.conf\n"
    )
    parsed = parse_dockerfile_copies(good_snippet)
    if parsed != [
        ("index.html", "/usr/share/nginx/html/index.html"),
        ("404.html", "/usr/share/nginx/html/404.html"),
    ]:
        print(f"SELFTEST FAIL: regex parse drift on good snippet, got {parsed!r}")
        return 1

    print(f"SELFTEST: all {len(mutations)} mutations caught + regex parse locked")
    return 0


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return selftest()
    return golden()


if __name__ == "__main__":
    raise SystemExit(main())
