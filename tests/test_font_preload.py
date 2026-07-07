"""
Font preload / stylesheet URL agreement contract.

Why: index.html:44-49 documents a real perf-regression class in an inline
comment — the Filament Group async-font pattern uses TWO `<link>` tags
(`rel="preload" as="style"` + `rel="stylesheet" media="print" onload=...`)
plus a `<noscript>` fallback. If any of those `href` values drift apart, the
preload no longer warms the cache used by the render-blocking stylesheet
and Chrome logs "The resource ... was preloaded ... but not used within a
few seconds." The measured cost per that comment is ~800ms of blocking
FCP/LCP time on Lighthouse mobile (wastedMs=786, 2026-07-05).

None of the seven existing stdlib suites assert on this: JSON-LD, OG,
assets, anchors, form, nginx, seo-files all leave the font URLs unchecked.
This closes the gap. Stdlib only (`re`, `pathlib`, `sys`).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = REPO_ROOT / "index.html"
NOT_FOUND = REPO_ROOT / "404.html"

# Match a <link ...> tag. Non-greedy so we don't swallow multiple tags.
LINK_RE = re.compile(r"<link\b([^>]*?)/?>", re.IGNORECASE | re.DOTALL)
# Attribute grabber: handles both quoted values and bare boolean tokens.
ATTR_RE = re.compile(r"""([a-zA-Z_:-]+)\s*=\s*(?P<q>["'])(.*?)(?P=q)""", re.DOTALL)

GFONTS_HOST = "fonts.googleapis.com/css2"


def _attrs(tag_body: str) -> dict[str, str]:
    return {m.group(1).lower(): m.group(3) for m in ATTR_RE.finditer(tag_body)}


def _strip_html_comments(html: str) -> str:
    """
    Remove <!-- ... --> blocks. index.html:44-49 has the STRING `<noscript>`
    inside a comment (explaining the async-font pattern) — without this pass
    the naive noscript extractor pairs comment-`<noscript>` on L47 with real
    `</noscript>` on L53 and swallows the actual <link> tags between them.
    Same pattern used in tests/test_nginx_headers.py's _strip_comments.
    """
    return re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)


def _font_link_hrefs(html: str) -> list[tuple[str, str]]:
    """
    Return every (role, href) pair for <link> tags referencing Google Fonts.
    Role is derived from rel/onload so callers can tell preload vs. stylesheet
    vs. noscript-fallback apart without re-parsing.
    """
    html = _strip_html_comments(html)
    out: list[tuple[str, str]] = []
    # <noscript>...</noscript> hides its <link> from the outer LINK_RE walk on
    # some regex engines, so pull noscript-nested links out explicitly first.
    for ns in re.finditer(r"<noscript>(.*?)</noscript>", html, re.DOTALL | re.IGNORECASE):
        for m in LINK_RE.finditer(ns.group(1)):
            attrs = _attrs(m.group(1))
            href = attrs.get("href", "")
            if GFONTS_HOST in href:
                out.append(("noscript", href))
    # Strip noscript blocks from the outer walk so we don't double-count.
    outer = re.sub(r"<noscript>.*?</noscript>", "", html, flags=re.DOTALL | re.IGNORECASE)
    for m in LINK_RE.finditer(outer):
        attrs = _attrs(m.group(1))
        href = attrs.get("href", "")
        if GFONTS_HOST not in href:
            continue
        rel = attrs.get("rel", "").lower()
        if "preload" in rel:
            out.append(("preload", href))
        elif "stylesheet" in rel:
            out.append(("stylesheet", href))
        else:
            out.append((rel or "link", href))
    return out


def assert_font_urls_agree(path: Path) -> list[str]:
    errors: list[str] = []
    html = path.read_text(encoding="utf-8")
    pairs = _font_link_hrefs(html)
    if not pairs:
        errors.append(f"{path.name}: no <link> pointing at {GFONTS_HOST} found")
        return errors

    # (1) All Google Fonts URLs on this page must be byte-identical — otherwise
    # the preload doesn't warm the fetch cache used by the stylesheet.
    hrefs = {href for _, href in pairs}
    if len(hrefs) != 1:
        errors.append(
            f"{path.name}: Google Fonts href drift — {len(hrefs)} distinct URLs across "
            f"{len(pairs)} <link> tags: {sorted(hrefs)}"
        )

    # (2) The URL must be https. HTTP triggers mixed-content blocking on
    # https:// deploys and silently kills the font fetch.
    for role, href in pairs:
        if not href.startswith("https://"):
            errors.append(f"{path.name}: {role} href not https: {href!r}")

    # (3) The URL must carry `display=swap`. Anything else (or missing) means
    # FOIT (invisible text until fonts load) — measurable Lighthouse hit.
    for role, href in pairs:
        if "display=swap" not in href:
            errors.append(f"{path.name}: {role} href missing display=swap: {href!r}")

    # (4) There must be at least one preload AND at least one stylesheet-fallback
    # pathway (either a media=print stylesheet or a noscript stylesheet). A page
    # with only a preload never applies the CSS.
    roles = {role for role, _ in pairs}
    if "preload" not in roles:
        errors.append(f"{path.name}: no rel=preload for Google Fonts (async pattern broken)")
    if not (roles & {"stylesheet", "noscript"}):
        errors.append(f"{path.name}: no stylesheet/noscript fallback for Google Fonts")

    return errors


# ─── selftest ────────────────────────────────────────────────────────────────

_VALID_INDEX = """<!doctype html><html><head>
<link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Inter&display=swap" />
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter&display=swap" media="print" onload="this.media='all'" />
<noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter&display=swap" /></noscript>
</head><body></body></html>"""


def _mutate(html: str, old: str, new: str) -> str:
    if old not in html:
        raise AssertionError(f"selftest mutation target not present: {old!r}")
    return html.replace(old, new, 1)


def selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "page.html"
        tmp.write_text(_VALID_INDEX, encoding="utf-8")
        if assert_font_urls_agree(tmp):
            print("SELFTEST FAIL: baseline should PASS", file=sys.stderr)
            return 1

        cases: list[tuple[str, str, str]] = [
            # (label, expected error substring, mutated html)
            (
                "preload href drift",
                "href drift",
                _mutate(
                    _VALID_INDEX,
                    'rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Inter&display=swap"',
                    'rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Roboto&display=swap"',
                ),
            ),
            (
                "stylesheet href drift",
                "href drift",
                _mutate(
                    _VALID_INDEX,
                    'rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter&display=swap" media="print"',
                    'rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400&display=swap" media="print"',
                ),
            ),
            (
                "noscript href drift",
                "href drift",
                _mutate(
                    _VALID_INDEX,
                    '<noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter&display=swap" /></noscript>',
                    '<noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@500&display=swap" /></noscript>',
                ),
            ),
            (
                "http not https",
                "not https",
                _VALID_INDEX.replace("https://fonts.googleapis.com", "http://fonts.googleapis.com"),
            ),
            (
                "missing display=swap",
                "display=swap",
                _VALID_INDEX.replace("&display=swap", ""),
            ),
            (
                "preload removed",
                "no rel=preload",
                _mutate(
                    _VALID_INDEX,
                    '<link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Inter&display=swap" />\n',
                    "",
                ),
            ),
            (
                "stylesheet + noscript both removed",
                "no stylesheet/noscript fallback",
                re.sub(
                    r'<link rel="stylesheet"[^>]+>|<noscript>.*?</noscript>',
                    "",
                    _VALID_INDEX,
                    flags=re.DOTALL,
                ),
            ),
            (
                "no google fonts link at all",
                "no <link>",
                re.sub(r'<link[^>]+fonts\.googleapis[^>]+>', "", _VALID_INDEX)
                .replace("<noscript>", "<noscript><!-- ")
                .replace("</noscript>", " --></noscript>"),
            ),
        ]

        # Regression probe: a `<noscript>` literal inside an HTML comment used
        # to pair with the real </noscript> further down and swallow the two
        # real <link> tags in between. The _strip_html_comments pass must
        # neutralize that; a valid page with a comment-<noscript> must PASS.
        comment_probe = _VALID_INDEX.replace(
            "<head>",
            "<head>\n<!-- explaining the pattern: <noscript> covers JS-off -->",
        )
        tmp.write_text(comment_probe, encoding="utf-8")
        if assert_font_urls_agree(tmp):
            print(
                "SELFTEST FAIL: comment-embedded <noscript> broke the parser",
                file=sys.stderr,
            )
            return 1

        misses: list[str] = []
        for label, expect, mutated in cases:
            tmp.write_text(mutated, encoding="utf-8")
            errs = assert_font_urls_agree(tmp)
            if not errs:
                misses.append(f"mutation not caught: {label}")
                continue
            if not any(expect in e for e in errs):
                misses.append(f"mutation caught but wrong reason for {label!r}: got {errs!r}, wanted substring {expect!r}")

        if misses:
            for m in misses:
                print(f"SELFTEST FAIL: {m}", file=sys.stderr)
            return 1

    print(f"SELFTEST OK: baseline PASS + {len(cases)}/{len(cases)} mutations caught")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    errors: list[str] = []
    for p in (INDEX, NOT_FOUND):
        if not p.exists():
            errors.append(f"{p} not found")
            continue
        errors.extend(assert_font_urls_agree(p))

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(f"OK: font preload/stylesheet/noscript hrefs agree on both index.html + 404.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
