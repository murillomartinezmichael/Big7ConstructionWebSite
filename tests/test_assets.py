"""
On-disk asset existence + magic-byte contract test.

Why: `test_jsonld.py` and `test_og_twitter.py` assert the URL strings for
`image`/`logo`/`og:image`/`twitter:image`, but neither test opens the byte at
that URL. A `git rm images/og-card.png` (or a rename typo in a future edit)
would leave all URL-string tests green while every social share preview 404s
and Google's rich-result crawler drops the logo. STATUS.md L15 explicitly
flagged this gap after tick 12 closed the meta-tag surface.

This test resolves every asset URL back to a local path via the canonical
origin declared in `index.html`, then asserts:
  1. The file exists on disk.
  2. The file is non-empty.
  3. Extension magic bytes match (PNG `\\x89PNG\\r\\n\\x1a\\n`,
     JPEG `\\xff\\xd8\\xff`) — catches "renamed .jpg to .png without
     re-encoding" and truncated-download regressions.

Coverage: JSON-LD `image` (string or list) + `logo.url` / `logo.contentUrl`
from `index.html`; `og:image` + `twitter:image` from BOTH `index.html` and
`404.html`.

Python 3.11+ stdlib only (`json`, `re`, `pathlib`, `urllib.parse`).
No pip install, no network.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "index.html"
NOT_FOUND = REPO_ROOT / "404.html"

CANONICAL_RE = re.compile(
    r'<link\s+rel=(?P<q>["\'])canonical(?P=q)\s+href=(?P<q2>["\'])(?P<href>[^"\']+)(?P=q2)',
    re.IGNORECASE,
)
JSONLD_RE = re.compile(
    r'<script[^>]+type=(?P<q>["\'])application/ld\+json(?P=q)[^>]*>(?P<body>.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
META_TAG_RE = re.compile(r'<meta\b[^>]*/?>', re.IGNORECASE)
ATTR_KEY_RE = re.compile(
    r'\b(?:property|name)\s*=\s*(?P<q>["\'])(?P<val>[^"\']+)(?P=q)',
    re.IGNORECASE,
)
ATTR_CONTENT_RE = re.compile(
    r'\bcontent\s*=\s*(?P<q>["\'])(?P<val>.*?)(?P=q)',
    re.IGNORECASE | re.DOTALL,
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"


def canonical_origin(html: str) -> str:
    m = CANONICAL_RE.search(html)
    if m is None:
        raise ValueError("no <link rel=\"canonical\"> tag found — cannot resolve asset URLs")
    parsed = urlparse(m.group("href"))
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"canonical href is not absolute: {m.group('href')!r}")
    return f"{parsed.scheme}://{parsed.netloc}"


def extract_jsonld_asset_urls(html: str) -> list[tuple[str, str]]:
    """Return [(source_label, url), ...] from JSON-LD image + logo fields."""
    out: list[tuple[str, str]] = []
    for m in JSONLD_RE.finditer(html):
        data = json.loads(m.group("body"))
        blocks = data if isinstance(data, list) else [data]
        for block in blocks:
            img = block.get("image")
            if isinstance(img, str):
                out.append(("jsonld.image", img))
            elif isinstance(img, list):
                for i, entry in enumerate(img):
                    if isinstance(entry, str):
                        out.append((f"jsonld.image[{i}]", entry))
            logo = block.get("logo")
            if isinstance(logo, str):
                out.append(("jsonld.logo", logo))
            elif isinstance(logo, dict):
                for key in ("url", "contentUrl"):
                    val = logo.get(key)
                    if isinstance(val, str):
                        out.append((f"jsonld.logo.{key}", val))
    return out


def extract_meta_asset_urls(html: str, label_prefix: str) -> list[tuple[str, str]]:
    """Return [(source_label, url), ...] from og:image + twitter:image meta tags."""
    tags: dict[str, str] = {}
    for tag in META_TAG_RE.findall(html):
        key_m = ATTR_KEY_RE.search(tag)
        content_m = ATTR_CONTENT_RE.search(tag)
        if key_m is None or content_m is None:
            continue
        tags[key_m.group("val").lower()] = content_m.group("val")
    out: list[tuple[str, str]] = []
    for key in ("og:image", "twitter:image"):
        val = tags.get(key)
        if val:
            out.append((f"{label_prefix}.{key}", val))
    return out


def url_to_local_path(url: str, origin: str, repo_root: Path) -> Path:
    if not url.startswith(origin + "/"):
        raise ValueError(
            f"asset URL {url!r} does not start with canonical origin {origin!r} — "
            f"cannot resolve to a local path"
        )
    rel = url[len(origin) + 1:]
    return repo_root / rel


def check_asset(url: str, origin: str, repo_root: Path) -> str | None:
    """Return None on success, error string on failure."""
    try:
        path = url_to_local_path(url, origin, repo_root)
    except ValueError as e:
        return str(e)
    if not path.exists():
        return f"asset {url!r} resolves to {path} but that file does not exist"
    if not path.is_file():
        return f"asset {url!r} resolves to {path} but that is not a regular file"
    size = path.stat().st_size
    if size == 0:
        return f"asset {url!r} exists at {path} but is zero bytes"
    ext = path.suffix.lower()
    if ext in (".png", ".jpg", ".jpeg"):
        expected = PNG_MAGIC if ext == ".png" else JPEG_MAGIC
        with path.open("rb") as f:
            head = f.read(len(expected))
        if not head.startswith(expected):
            kind = "PNG" if ext == ".png" else "JPEG"
            return (
                f"asset {url!r} at {path} has extension {ext} but does not carry the "
                f"{kind} magic-byte prefix — either the file is corrupt/truncated or "
                f"was renamed from a different format"
            )
    return None


def _valid_asset_set(repo_root: Path) -> tuple[str, list[tuple[str, str]]]:
    """Baseline for selftest: refs all existing images in ./images/."""
    origin = "https://big7construction.com"
    urls = [
        ("jsonld.image[0]", f"{origin}/images/og-card.png"),
        ("jsonld.image[1]", f"{origin}/images/jobsite-01.jpg"),
        ("jsonld.logo.url", f"{origin}/images/og-card.png"),
        ("index.og:image", f"{origin}/images/og-card.png"),
        ("index.twitter:image", f"{origin}/images/og-card.png"),
        ("404.og:image", f"{origin}/images/og-card.png"),
        ("404.twitter:image", f"{origin}/images/og-card.png"),
    ]
    return origin, urls


def selftest(repo_root: Path) -> int:
    origin, baseline = _valid_asset_set(repo_root)
    errors = [check_asset(url, origin, repo_root) for _, url in baseline]
    errors = [e for e in errors if e is not None]
    if errors:
        for e in errors:
            print(f"SELFTEST FAIL (baseline): {e}", file=sys.stderr)
        return 1

    # Build a scratch tree for mutations that need synthetic files on disk.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        (tmp_root / "images").mkdir()
        (tmp_root / "images" / "og-card.png").write_bytes(PNG_MAGIC + b"stub")
        (tmp_root / "images" / "jobsite-01.jpg").write_bytes(JPEG_MAGIC + b"stub")
        (tmp_root / "images" / "empty.png").write_bytes(b"")
        (tmp_root / "images" / "wrong-magic.png").write_bytes(b"NOT-A-PNG")
        (tmp_root / "images" / "renamed.png").write_bytes(JPEG_MAGIC + b"stub")

        cases: list[tuple[str, str]] = [
            ("missing file",       f"{origin}/images/does-not-exist.png"),
            ("wrong subdir",       f"{origin}/img/og-card.png"),
            ("empty file",         f"{origin}/images/empty.png"),
            ("wrong magic bytes",  f"{origin}/images/wrong-magic.png"),
            ("renamed jpg to png", f"{origin}/images/renamed.png"),
            ("wrong origin",       "https://other.example.com/images/og-card.png"),
            ("http not https",     f"http://big7construction.com/images/og-card.png"),
            ("relative url",       "/images/og-card.png"),
        ]
        # Sanity-check each synthetic file first: prove that "empty" / "wrong magic"
        # actually fail against tmp_root before we assert real regressions do too.
        misses: list[str] = []
        for name, url in cases:
            err = check_asset(url, origin, tmp_root)
            if err is None:
                misses.append(name)
        if misses:
            for name in misses:
                print(f"SELFTEST FAIL: mutation not caught: {name}", file=sys.stderr)
            return 1

    print(f"SELFTEST OK: baseline PASS + {len(cases)}/{len(cases)} mutations caught")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest(REPO_ROOT)

    if not INDEX.exists():
        print(f"FAIL: {INDEX} not found", file=sys.stderr)
        return 1

    index_html = INDEX.read_text(encoding="utf-8")
    origin = canonical_origin(index_html)

    assets: list[tuple[str, str]] = []
    assets.extend(extract_jsonld_asset_urls(index_html))
    assets.extend(extract_meta_asset_urls(index_html, "index"))
    if NOT_FOUND.exists():
        assets.extend(extract_meta_asset_urls(NOT_FOUND.read_text(encoding="utf-8"), "404"))

    if not assets:
        print("FAIL: no asset URLs discovered in JSON-LD or meta tags", file=sys.stderr)
        return 1

    errors: list[str] = []
    for label, url in assets:
        err = check_asset(url, origin, REPO_ROOT)
        if err is not None:
            errors.append(f"{label}: {err}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    unique_urls = sorted({u for _, u in assets})
    print(
        f"OK: {len(assets)} asset references ({len(unique_urls)} unique URLs) all resolve "
        f"to on-disk files with matching magic bytes"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
