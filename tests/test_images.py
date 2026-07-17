"""
Image contract test.

Why: no existing suite locks the <img> WCAG 1.1.1 alt-text baseline, the LCP
hero preload <-> <img src> agreement, or the perf-hint pair (fetchpriority=high
on the hero, decoding=async on below-fold cards). Alt text drives the a11y
score + image SEO; a preload URL that drifts from the actual <img src> warms
an unused cache slot and silently regresses LCP; stripping decoding=async
from a lazy card leaves main-thread jank on scroll. `test_assets.py` walks
JSON-LD / OG / Twitter URLs only -- it does NOT open the in-page <img src>
files, and no other test asserts alt-text or the perf-hint pair.

Locks (index.html):
  1. Every <img> has a non-empty alt attribute (WCAG 1.1.1 Level A).
  2. Every <img src> is a relative path starting with `images/` (local,
     no accidental external CDN).
  3. Every <img src> resolves to a real on-disk file under images/.
  4. Exactly one <img> carries fetchpriority="high" (single, unambiguous
     LCP hint -- multiple hints defeat the point).
  5. The <link rel="preload" as="image"> href agrees byte-for-byte with
     the fetchpriority=high <img src> (else the preload warms a cache
     slot no <img> ever consumes).
  6. Every <img loading="lazy"> also carries decoding="async" (perf-hint
     pair -- lazy defers fetch, async defers decode; separating them
     leaves the wrong half of the pair on the main thread).
  7. Total <img> count is at or above MIN_IMGS floor (guards a silent
     mass-delete regression of the portfolio grid).

Python 3.11+ stdlib only (`re`, `pathlib`, `sys`, `tempfile`). No pip
install, no network.
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "index.html"
IMAGES_DIR = REPO_ROOT / "images"

# Per-page floors (2026-07-17 two-path restructure): the chooser homepage
# keeps only the hero image; the portfolio grids live on the lane pages.
MIN_IMGS = 6  # selftest fixture floor; real pages use PAGES below
PAGES = (
    # (path, min imgs, require LCP hints: fetchpriority=high + preload-as-image)
    ("index.html", 1, True),
    ("commercial-industrial.html", 4, False),
    ("residential-construction.html", 2, False),
)

IMG_TAG_RE = re.compile(r'<img\b(?P<attrs>[^>]*)/?>', re.IGNORECASE)
PRELOAD_IMAGE_RE = re.compile(
    r'<link\b(?P<attrs>[^>]*)/?>',
    re.IGNORECASE,
)


def _attr(name: str, attrs: str) -> str | None:
    m = re.search(
        rf'\b{re.escape(name)}\s*=\s*(?P<q>["\'])(?P<val>.*?)(?P=q)',
        attrs,
        re.IGNORECASE | re.DOTALL,
    )
    return m.group("val") if m else None


def _preload_image_hrefs(html: str) -> list[str]:
    hrefs: list[str] = []
    for m in PRELOAD_IMAGE_RE.finditer(html):
        attrs = m.group("attrs")
        rel = (_attr("rel", attrs) or "").lower()
        as_ = (_attr("as", attrs) or "").lower()
        if rel == "preload" and as_ == "image":
            href = _attr("href", attrs)
            if href is not None:
                hrefs.append(href)
    return hrefs


def check(
    html: str,
    images_dir: Path | None = None,
    min_imgs: int = MIN_IMGS,
    require_lcp_hints: bool = True,
) -> list[str]:
    errors: list[str] = []
    imgs = list(IMG_TAG_RE.finditer(html))

    if len(imgs) < min_imgs:
        errors.append(
            f'<img> count = {len(imgs)}; below floor {min_imgs} '
            f'-- hero / portfolio grid collapsed?'
        )

    fp_high_srcs: list[str] = []

    for i, m in enumerate(imgs):
        attrs = m.group("attrs")
        src = _attr("src", attrs)
        alt = _attr("alt", attrs)
        loading = (_attr("loading", attrs) or "").lower()
        decoding = (_attr("decoding", attrs) or "").lower()
        fp = (_attr("fetchpriority", attrs) or "").lower()
        label = f'<img #{i + 1} src={src!r}>'

        if alt is None:
            errors.append(f'{label}: missing alt attribute -- WCAG 1.1.1 fail')
        elif not alt.strip():
            errors.append(
                f'{label}: empty alt -- WCAG 1.1.1 requires non-empty alt '
                f'for content images (empty alt only valid for pure decoration)'
            )

        if src is None:
            errors.append(f'{label}: missing src attribute')
        else:
            if src.startswith(("http://", "https://", "//")):
                errors.append(
                    f'{label}: src is an external URL -- expected a local '
                    f'`images/...` path'
                )
            elif not src.startswith("images/"):
                errors.append(
                    f'{label}: src {src!r} does not start with `images/` '
                    f'-- expected a relative path inside the images/ dir'
                )
            elif images_dir is not None:
                on_disk = images_dir / Path(src).name
                if not on_disk.is_file():
                    errors.append(
                        f'{label}: src {src!r} does not resolve to an on-disk '
                        f'file at {on_disk} (git rm without href update?)'
                    )

        if fp == "high" and src is not None:
            fp_high_srcs.append(src)

        if loading == "lazy" and decoding != "async":
            errors.append(
                f'{label}: loading="lazy" without decoding="async" -- perf-hint '
                f'pair; lazy defers fetch, async defers decode, separating them '
                f'leaves main-thread jank on scroll'
            )

    if not fp_high_srcs:
        if require_lcp_hints:
            errors.append(
                'no <img fetchpriority="high"> found -- LCP element has no '
                'priority hint; browser will guess and often guess wrong'
            )
    elif len(fp_high_srcs) > 1:
        errors.append(
            f'multiple <img fetchpriority="high"> ({len(fp_high_srcs)}: '
            f'{fp_high_srcs}) -- LCP hint must be unique or the browser '
            f'has to arbitrate between competing "highest" claims'
        )

    preload_hrefs = _preload_image_hrefs(html)
    if not preload_hrefs:
        if require_lcp_hints:
            errors.append(
                'no <link rel="preload" as="image"> found -- hero image is not '
                'warmed at parse time; LCP will pay the full network round-trip'
            )
    elif fp_high_srcs and not any(h == fp_high_srcs[0] for h in preload_hrefs):
        errors.append(
            f'<link rel="preload" as="image"> href set {preload_hrefs} does '
            f'not include the fetchpriority="high" <img> src '
            f'{fp_high_srcs[0]!r} -- preload warms an unused cache slot'
        )

    return errors


# ---------------------------------------------------------------------------
# --selftest
# ---------------------------------------------------------------------------

def _valid_html(min_imgs: int = MIN_IMGS) -> str:
    hero = (
        '<img src="images/hero.jpg" alt="Hero photo" '
        'fetchpriority="high" onerror="this.style.display=\'none\'" />'
    )
    below = "\n".join(
        f'<img src="images/pf-{i}.jpg" alt="Portfolio card {i}" '
        f'loading="lazy" decoding="async" />'
        for i in range(min_imgs - 1)
    )
    preload = '<link rel="preload" as="image" href="images/hero.jpg" />'
    return (
        '<!doctype html><html lang="en"><head>'
        f'{preload}'
        '</head><body>'
        f'{hero}\n{below}'
        '</body></html>'
    )


def _fake_images_dir(tmp_root: Path, min_imgs: int = MIN_IMGS) -> Path:
    d = tmp_root / "images"
    d.mkdir(parents=True, exist_ok=True)
    (d / "hero.jpg").write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")
    for i in range(min_imgs - 1):
        (d / f"pf-{i}.jpg").write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")
    return d


def _selftest() -> None:
    baseline = _valid_html()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        imgs_dir = _fake_images_dir(tmp)

        errs = check(baseline, imgs_dir)
        assert not errs, f'baseline should PASS but got: {errs}'

        one_img_html = (
            '<!doctype html><html><head>'
            '<link rel="preload" as="image" href="images/hero.jpg" />'
            '</head><body>'
            '<img src="images/hero.jpg" alt="Hero" fetchpriority="high" />'
            '</body></html>'
        )

        mutations: list[tuple[str, str, str]] = [
            (
                'alt stripped from hero',
                re.sub(r'alt="Hero photo"\s?', '', baseline),
                'missing alt attribute',
            ),
            (
                'empty alt on hero',
                baseline.replace('alt="Hero photo"', 'alt=""'),
                'empty alt',
            ),
            (
                'src pointed at external CDN',
                baseline.replace(
                    'src="images/hero.jpg"',
                    'src="https://cdn.example.com/hero.jpg"',
                    1,
                ),
                'external URL',
            ),
            (
                'src outside images/ dir',
                baseline.replace(
                    'src="images/hero.jpg"', 'src="assets/hero.jpg"', 1,
                ).replace(
                    'href="images/hero.jpg"', 'href="assets/hero.jpg"', 1,
                ),
                'start with `images/`',
            ),
            (
                'src references missing on-disk file',
                baseline.replace('images/hero.jpg', 'images/nope.jpg'),
                'does not resolve to an on-disk file',
            ),
            (
                'fetchpriority stripped from hero',
                baseline.replace(' fetchpriority="high"', ''),
                'no <img fetchpriority="high">',
            ),
            (
                'two <img fetchpriority="high">',
                baseline.replace(
                    'loading="lazy" decoding="async"',
                    'loading="lazy" decoding="async" fetchpriority="high"',
                    1,
                ),
                'multiple <img fetchpriority="high"',
            ),
            (
                'preload href drift from hero src',
                baseline.replace(
                    '<link rel="preload" as="image" href="images/hero.jpg" />',
                    '<link rel="preload" as="image" href="images/wrong.jpg" />',
                ),
                'does not include the fetchpriority="high"',
            ),
            (
                'lazy without decoding=async',
                baseline.replace(
                    'loading="lazy" decoding="async"', 'loading="lazy"', 1,
                ),
                'without decoding="async"',
            ),
            (
                'below MIN_IMGS floor',
                one_img_html,
                'below floor',
            ),
            (
                'preload <link> removed entirely',
                baseline.replace(
                    '<link rel="preload" as="image" href="images/hero.jpg" />',
                    '',
                ),
                'no <link rel="preload" as="image">',
            ),
        ]

        for label, mutated, needle in mutations:
            errs = check(mutated, imgs_dir)
            if not errs:
                raise AssertionError(
                    f'mutation {label!r} should FAIL but check() returned no errors'
                )
            joined = " | ".join(errs)
            if needle not in joined:
                raise AssertionError(
                    f'mutation {label!r} raised errors, but none contained '
                    f'{needle!r}: {errs}'
                )

    print(
        f'OK: baseline PASS + {len(mutations)}/{len(mutations)} mutations caught'
    )


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
        return 0

    total = 0
    failed = False
    for name, min_imgs, require_lcp in PAGES:
        path = REPO_ROOT / name
        if not path.is_file():
            print(f'FAIL: {path} missing', file=sys.stderr)
            failed = True
            continue
        html = path.read_text(encoding="utf-8")
        errs = check(html, IMAGES_DIR, min_imgs=min_imgs, require_lcp_hints=require_lcp)
        if errs:
            print(f'FAIL: <img> contract violations on {name}:', file=sys.stderr)
            for e in errs:
                print('  -', e, file=sys.stderr)
            failed = True
            continue
        total += len(list(IMG_TAG_RE.finditer(html)))
    if failed:
        return 1

    print(
        f'OK: {total} <img> tags across {len(PAGES)} pages; all alts non-empty; '
        f'index hero fp=high + <link rel=preload as=image> href agree; every '
        f'loading=lazy carries decoding=async'
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
