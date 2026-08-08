"""
Shipped-source leak lock: what the deploy publishes, and what it says.

Why: `wrangler.jsonc` sets `assets.directory: "./"`, so on Cloudflare Workers
-- the host of record -- the repo root IS the document root. Until 2026-08-08
there was no `.assetsignore`, and every tracked file was live on the client's
production domain: PENDING_MANUAL.md, TODO.md, DECISIONS.md, CLAUDE.md, the
test suite, .env.example, and .git/config all returned HTTP 200. Separately,
the pages themselves carried HTML/CSS/JS comments naming our LAW numbers, our
internal filenames, and an admission that a client testimonial had no
documented source. Both classes ship to anyone who types the URL or hits
"view source". See docs/shipped-source-hygiene.md.

Neither class produces a visible symptom, so only a test catches the
regression. Stdlib only so `python tests/test_shipped_source.py` runs on any
Python 3.11+ machine with zero setup.

Checks:
  1. `.assetsignore` exists and is non-empty.
  2. The public surface is derived from the Dockerfile's explicit COPY list
     (the Railway/nginx fallback ships exactly those paths). Every one of
     those public paths must NOT be excluded by `.assetsignore` -- an
     over-broad pattern that silently unpublishes the live site fails here.
  3. Every other file in the repo tree IS excluded by `.assetsignore`. Add a
     new internal file and this fails until the path is covered.
  4. No file on the public surface contains an internal-governance marker
     (LAW numbers, PENDING_MANUAL / DECISIONS.md / TODO.md / CONVERSION_
     STANDARDS.md / SECURITY_AUDIT.md pointers, tests/ or scripts/ paths,
     bare test_*.py names, SiteAudit finding ids, tick-N session names).

Run:
    python tests/test_shipped_source.py            # golden check on the real files
    python tests/test_shipped_source.py --selftest # mutate baseline, expect each broken variant to fail
"""

from __future__ import annotations

import fnmatch
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories we never even walk: not deploy input on a clean CI clone, and
# walking them locally is slow and noisy.
SKIP_WALK = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache"}

# Consumed by the Cloudflare Workers assets pipeline rather than served.
# Verified live 2026-08-08: both return 404 on the production domain. They are
# deliberately NOT listed in .assetsignore -- excluding them risks Cloudflare
# never reading them, which would drop the five security headers and the
# /home-repair 301.
CF_CONSUMED = {"_headers", "_redirects"}

# Text extensions worth scanning for leaked internal references. Binary assets
# (images, the capability-statement PDF) are skipped.
TEXT_SUFFIXES = {".html", ".js", ".css", ".xml", ".txt", ".json"}

# Internal-governance markers that must never appear in a public file.
# (label, compiled pattern)
LEAK_PATTERNS = [
    ("LAW number", re.compile(r"\bLAW\s*#?\d")),
    ("PENDING_MANUAL", re.compile(r"PENDING_MANUAL")),
    ("internal .md pointer", re.compile(r"\b(DECISIONS|TODO|STATUS|CHANGELOG|BRD|TRD|RUNBOOK|ONBOARDING|CONTENT|AGENTS|CLAUDE|CONVERSION_STANDARDS|SECURITY_AUDIT|SESSION_GOAL)\.md")),
    ("internal path", re.compile(r"\b(tests|scripts)/[A-Za-z0-9_.\-]+")),
    ("test module name", re.compile(r"\btest_[a-z0-9_]+\.py")),
    ("SiteAudit finding id", re.compile(r"SiteAudit")),
    ("session/tick name", re.compile(r"\btick-\d+")),
]


# ── .assetsignore -------------------------------------------------------


def load_patterns(path: Path) -> list[str]:
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def is_excluded(rel: str, patterns: list[str]) -> str | None:
    """Return the matching pattern, or None. gitignore-style, deny-list only."""
    rel = rel.replace("\\", "/")
    base = rel.rsplit("/", 1)[-1]
    for p in patterns:
        if p.endswith("/"):
            d = p[:-1]
            # Directory pattern: matches that directory at any depth.
            if rel == d or rel.startswith(d + "/") or ("/" + d + "/") in ("/" + rel):
                return p
        elif "/" in p:
            if rel == p or rel.startswith(p + "/"):
                return p
        else:
            if fnmatch.fnmatch(base, p) or fnmatch.fnmatch(rel, p):
                return p
    return None


# ── public surface ------------------------------------------------------


def public_paths(repo: Path) -> list[str]:
    """Repo-relative paths the Dockerfile publishes (its COPY list, minus the
    nginx config, which is copied into /etc not the document root)."""
    out: list[str] = []
    for line in (repo / "Dockerfile").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^COPY\s+(\S+)\s+(\S+)\s*$", line.strip())
        if not m:
            continue
        src, dst = m.group(1), m.group(2)
        if not dst.startswith("/usr/share/nginx/html"):
            continue
        if src.endswith("/"):
            d = repo / src
            if d.is_dir():
                out.extend(
                    str(f.relative_to(repo)).replace("\\", "/")
                    for f in sorted(d.rglob("*"))
                    if f.is_file()
                )
        else:
            out.append(src.replace("\\", "/"))
    return sorted(set(out))


def walk_repo(repo: Path) -> list[str]:
    out = []
    for f in repo.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(repo).as_posix()
        if any(part in SKIP_WALK for part in rel.split("/")[:-1]):
            continue
        if rel.split("/")[0] in SKIP_WALK:
            continue
        out.append(rel)
    return sorted(out)


# ── checks --------------------------------------------------------------


def run_all_checks(repo: Path) -> list[str]:
    errors: list[str] = []

    ignore = repo / ".assetsignore"
    if not ignore.is_file():
        return [
            ".assetsignore is missing -- wrangler.jsonc serves the whole repo "
            "root, so every internal file would be live on the client's domain"
        ]
    patterns = load_patterns(ignore)
    if not patterns:
        return [".assetsignore has no patterns"]

    public = public_paths(repo)
    if not public:
        return ["could not derive the public surface from the Dockerfile COPY list"]
    public_set = set(public)

    # 2. public files must stay publishable
    for rel in public:
        hit = is_excluded(rel, patterns)
        if hit:
            errors.append(
                f"{rel} is on the public surface (Dockerfile COPY) but "
                f".assetsignore pattern {hit!r} excludes it -- this would "
                f"unpublish a live page"
            )

    # 3. everything else must be excluded
    for rel in walk_repo(repo):
        if rel in public_set or rel in CF_CONSUMED:
            continue
        if is_excluded(rel, patterns) is None:
            errors.append(
                f"{rel} is not on the public surface and no .assetsignore "
                f"pattern covers it -- it would be served at "
                f"https://big7construction.com/{rel}"
            )

    # 4. no internal references in what ships
    for rel in public:
        f = repo / rel
        if f.suffix.lower() not in TEXT_SUFFIXES or not f.is_file():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            for label, rx in LEAK_PATTERNS:
                m = rx.search(line)
                if m:
                    errors.append(
                        f"{rel}:{lineno} leaks {label} ({m.group(0)!r}) to the "
                        f"browser -- move the reasoning into the commit message "
                        f"or docs/shipped-source-hygiene.md"
                    )
    return errors


# ── selftest ------------------------------------------------------------


def selftest() -> int:
    """Mutate a copy of the baseline; every broken variant must fail."""
    baseline_errors = run_all_checks(REPO_ROOT)
    if baseline_errors:
        print("FAIL: baseline is not clean, cannot run --selftest", file=sys.stderr)
        for e in baseline_errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    def mutate_missing_ignore(root: Path) -> None:
        (root / ".assetsignore").unlink()

    def mutate_empty_ignore(root: Path) -> None:
        (root / ".assetsignore").write_text("# nothing\n", encoding="utf-8")

    def mutate_new_internal_file(root: Path) -> None:
        (root / "INTERNAL-NOTES.rst").write_text("secret\n", encoding="utf-8")

    def mutate_overbroad_pattern(root: Path) -> None:
        p = root / ".assetsignore"
        p.write_text(p.read_text(encoding="utf-8") + "\n*.html\n", encoding="utf-8")

    def mutate_law_comment(root: Path) -> None:
        p = root / "index.html"
        p.write_text(
            p.read_text(encoding="utf-8").replace(
                "</body>", "<!-- removed per LAW 6 -->\n</body>", 1
            ),
            encoding="utf-8",
        )

    def mutate_pending_manual_comment(root: Path) -> None:
        p = root / "big7.js"
        p.write_text(
            "// see PENDING_MANUAL.md\n" + p.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    def mutate_test_path_comment(root: Path) -> None:
        p = root / "sitemap.xml"
        p.write_text(
            p.read_text(encoding="utf-8").replace(
                "<urlset", "<!-- locked by tests/test_seo_files.py --><urlset", 1
            ),
            encoding="utf-8",
        )

    def mutate_siteaudit_comment(root: Path) -> None:
        p = root / "commercial-industrial.html"
        p.write_text(
            p.read_text(encoding="utf-8").replace(
                "</body>", "<!-- SiteAudit tap_target_size -->\n</body>", 1
            ),
            encoding="utf-8",
        )

    mutations = [
        ("missing .assetsignore", mutate_missing_ignore),
        ("empty .assetsignore", mutate_empty_ignore),
        ("new uncovered internal file", mutate_new_internal_file),
        ("over-broad pattern unpublishes pages", mutate_overbroad_pattern),
        ("LAW number in shipped HTML", mutate_law_comment),
        ("PENDING_MANUAL in shipped JS", mutate_pending_manual_comment),
        ("tests/ path in shipped XML", mutate_test_path_comment),
        ("SiteAudit id in shipped HTML", mutate_siteaudit_comment),
    ]

    failures = 0
    for name, mutate in mutations:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            shutil.copytree(
                REPO_ROOT,
                root,
                ignore=shutil.ignore_patterns(*SKIP_WALK),
            )
            mutate(root)
            if not run_all_checks(root):
                print(f"FAIL: mutation not caught -- {name}", file=sys.stderr)
                failures += 1
            else:
                print(f"  caught: {name}")

    if failures:
        return 1
    print(f"OK: selftest -- all {len(mutations)} broken variants rejected.")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    errors = run_all_checks(REPO_ROOT)
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    public = public_paths(REPO_ROOT)
    patterns = load_patterns(REPO_ROOT / ".assetsignore")
    print(
        f"OK: .assetsignore has {len(patterns)} pattern(s); the {len(public)} "
        f"public path(s) from the Dockerfile COPY list stay publishable; every "
        f"other file in the tree is excluded; no shipped file references LAW "
        f"numbers, internal docs, test paths, or session names."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
