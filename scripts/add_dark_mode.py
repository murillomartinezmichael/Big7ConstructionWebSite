"""Give every shipped page a dark mode without touching light mode.

Each page inlines its own CSS with mostly hardcoded colors, and some sections
(hero, footer) are dark in BOTH themes. Flipping a color everywhere would turn
those sections white, so colors are remapped by the ROLE they play:

  background  light surface      -> deep steel-blue surface (dark sections stay)
  text        dark ink           -> light ink; dark brand text -> lighter brand
  border      light hairline     -> dark hairline

Every rewritten value is `var(--dm-..., <original>)`. Nothing defines --dm-*
in light mode, so light mode renders the original color byte-for-byte.
theme.css defines them for dark mode; the generated block sits between the
markers there. Idempotent: values already holding var(--dm- are skipped.

    python scripts/add_dark_mode.py          # rewrite pages + regenerate theme.css
    python scripts/add_dark_mode.py --check  # exit 1 if a page needs rewriting
"""
import colorsys
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = sorted(p for p in ROOT.glob("*.html"))
THEME_CSS = ROOT / "theme.css"
START, END = "/* dark-palette:start (generated; do not hand-edit) */", "/* dark-palette:end */"
STEEL_HUE = 215 / 360  # brand blue: dark surfaces carry it instead of flat grey

TEXT_PROPS = {"color", "fill", "stroke", "caret-color", "text-decoration-color", "-webkit-text-fill-color", "accent-color"}
BG_PROPS = {"background", "background-color", "background-image"}
LINE_PREFIXES = ("border", "outline", "column-rule")

HEX = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
RGBA = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+%?)\s*)?\)")
VAR = re.compile(r"var\(\s*(--[\w-]+)\s*\)")


def norm(h):
    h = h.lstrip("#").lower()
    return "".join(c * 2 for c in h) if len(h) == 3 else h


def rgb(h):
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def luminance(h):
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb(h)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def hls_hex(hue, light, sat):
    r, g, b = colorsys.hls_to_rgb(hue, max(0, min(1, light)), max(0, min(1, sat)))
    return "#{:02x}{:02x}{:02x}".format(*(round(c * 255) for c in (r, g, b)))


def dark_for(role, h):
    """Dark-mode counterpart of color h in a role, or None to keep it as is."""
    hue, light, sat = colorsys.rgb_to_hls(*rgb(h))
    lum = luminance(h)
    neutral = sat < 0.28 or light > 0.93
    if role == "bg":
        if lum < 0.3:
            return None  # already a dark surface (hero, footer): stays dark
        if neutral:
            return hls_hex(STEEL_HUE, 0.075 + (1 - light) * 0.4, 0.24)
        return hls_hex(hue, 0.15 + (1 - light) * 0.2, min(sat, 0.6))
    if role == "text":
        if lum > 0.32:
            return None  # already light text (on a dark section)
        if neutral:
            return hls_hex(STEEL_HUE, 0.95 - light * 0.55, 0.14)
        return hls_hex(hue, max(light, 0.68), min(sat, 0.9))
    if role == "line":
        if lum < 0.4:
            return None
        if neutral:
            return hls_hex(STEEL_HUE, 0.2 + (1 - light) * 0.35, 0.2)
        return hls_hex(hue, 0.32, sat)
    return None


def role_of(prop):
    prop = prop.strip().lower()
    if prop in TEXT_PROPS:
        return "text"
    if prop in BG_PROPS:
        return "bg"
    if prop.startswith(LINE_PREFIXES) or prop == "box-shadow":
        return "line"
    return None


class Rewriter:
    def __init__(self):
        self.defs = {}      # --dm-name -> dark value
        self.root_vars = {}

    def collect_root_vars(self, css):
        for m in re.finditer(r":root\s*\{([^}]*)\}", css):
            for name, val in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", m.group(1)):
                hm = HEX.fullmatch(val.strip())
                if hm:
                    self.root_vars[name] = norm(hm.group(1))

    def redefine(self, name):
        """Re-derive a token from its name, so re-runs keep the full palette."""
        m = re.fullmatch(r"--dm-(bg|text|line)(c?)-([0-9a-f]{6})", name)
        if m:
            role, channels, h = m.groups()
            dark = dark_for(role, h)
            if role == "line" and channels and luminance(h) < 0.05:
                dark = "#ffffff"
            if dark:
                self.defs[name] = " ".join(str(int(dark[i:i + 2], 16)) for i in (1, 3, 5)) if channels else dark
            return
        m = re.fullmatch(r"--dm-(bg|text|line)(--[\w-]+)", name)
        if m and m.group(2) in self.root_vars:
            dark = dark_for(m.group(1), self.root_vars[m.group(2)])
            if dark:
                self.defs[name] = dark

    def value(self, role, value):
        if "var(--dm-" in value:
            for name in re.findall(r"var\((--dm-[\w-]+)", value):
                self.redefine(name)
            return value

        def hex_sub(m):
            h = norm(m.group(1))
            dark = dark_for(role, h)
            if not dark:
                return m.group(0)
            name = f"--dm-{role}-{h}"
            self.defs[name] = dark
            return f"var({name}, {m.group(0)})"

        def rgba_sub(m):
            r, g, b = (int(m.group(i)) for i in (1, 2, 3))
            h = "{:02x}{:02x}{:02x}".format(r, g, b)
            dark = dark_for(role, h)
            if role == "line" and luminance(h) < 0.05:
                dark = "#ffffff"  # dark hairline on light page -> light hairline on dark page
            if not dark:
                return m.group(0)
            alpha = m.group(4) or "1"
            name = f"--dm-{role}c-{h}"
            self.defs[name] = " ".join(str(int(dark[i:i + 2], 16)) for i in (1, 3, 5))
            return f"rgb(var({name}, {r} {g} {b}) / {alpha})"

        def var_sub(m):
            src = m.group(1)
            if src not in self.root_vars:
                return m.group(0)
            dark = dark_for(role, self.root_vars[src])
            if not dark:
                return m.group(0)
            name = f"--dm-{role}{src}"
            self.defs[name] = dark
            return f"var({name}, var({src}))"

        value = VAR.sub(var_sub, value)
        value = RGBA.sub(rgba_sub, value)
        # hex inside url(...) (inline SVG data URIs) must not be touched
        parts = re.split(r"(url\([^)]*\))", value)
        return "".join(p if p.startswith("url(") else HEX.sub(hex_sub, p) for p in parts)

    def declarations(self, body):
        def decl(m):
            prop, val = m.group(1), m.group(2)
            if prop.strip().startswith("--"):
                return m.group(0)  # token definitions stay; usages are remapped
            role = role_of(prop)
            return m.group(0) if not role else f"{prop}:{self.value(role, val)}"
        return re.sub(r"([\w-]+)\s*:((?:[^;{}\"']|\"[^\"]*\"|'[^']*')+)", decl, body)

    def css(self, css):
        # innermost rule bodies only, so selectors (a:hover) are never parsed as declarations
        return re.sub(r"\{([^{}]*)\}", lambda m: "{" + self.declarations(m.group(1)) + "}", css)

    def page(self, html):
        for m in re.finditer(r"<style[^>]*>(.*?)</style>", html, re.S):
            self.collect_root_vars(m.group(1))
        html = re.sub(r"(<style[^>]*>)(.*?)(</style>)", lambda m: m.group(1) + self.css(m.group(2)) + m.group(3), html, flags=re.S)
        return re.sub(r'(\sstyle=")([^"]*)(")', lambda m: m.group(1) + self.declarations(m.group(2)) + m.group(3), html)


HEAD_SNIPPET = """  <link rel="stylesheet" href="/theme.css" />
  <script>
    /* Before first paint: apply a saved light/dark choice (none = follow the OS). */
    try { var t = localStorage.getItem('big7-theme'); if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t; } catch (e) {}
  </script>
  <script defer src="/theme.js"></script>
"""


def main():
    check = "--check" in sys.argv
    rw = Rewriter()
    changed = []
    for page in PAGES:
        src = page.read_text(encoding="utf-8")
        out = rw.page(src)
        if "/theme.css" not in out:
            out = out.replace("</head>", HEAD_SNIPPET + "</head>", 1)
        if out != src:
            changed.append(page.name)
            if not check:
                page.write_text(out, encoding="utf-8", newline="")
    if check:
        print("needs rewrite:", ", ".join(changed) if changed else "none")
        return 1 if changed else 0
    tokens = sorted(rw.defs.items())
    block = lambda indent: "\n".join(f"{indent}{k}: {v};" for k, v in tokens) + f"\n{indent}color-scheme: dark;"
    palette = (f"{START}\n"
               f"@media (prefers-color-scheme: dark) {{\n  :root:not([data-theme=\"light\"]) {{\n{block('    ')}\n  }}\n}}\n"
               f":root[data-theme=\"dark\"] {{\n{block('  ')}\n}}\n{END}")
    css = THEME_CSS.read_text(encoding="utf-8")
    css = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: palette, css, flags=re.S)
    THEME_CSS.write_text(css, encoding="utf-8", newline="")
    print(f"rewrote {len(changed)} page(s): {', '.join(changed) or 'none'}; {len(rw.defs)} dark tokens")
    return 0


sys.exit(main())
