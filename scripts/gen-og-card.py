"""Generate the branded Open Graph card at images/og-card.png (1200x630).

Deterministic: rerunning produces byte-identical output on the same Pillow +
font set. Zero client photos required — this is a typography card matching the
site's paper/ink/accent palette so iMessage/Slack/Facebook show a clean preview
even while jobsite-01.jpg remains a 206x206 placeholder.

Run: `python scripts/gen-og-card.py`.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CARD_W = 1200
CARD_H = 630
PAPER = (245, 241, 234)
INK_950 = (8, 9, 11)
INK_500 = (76, 82, 88)
ACCENT = (179, 68, 25)
BLUE = (26, 106, 176)

WINDOWS_FONTS = Path("C:/Windows/Fonts")


def load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for name in candidates:
        p = WINDOWS_FONTS / name
        if p.exists():
            return ImageFont.truetype(str(p), size=size)
    return ImageFont.load_default()


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "images" / "og-card.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    display = load_font(["impact.ttf", "arialbd.ttf"], 118)
    subhead = load_font(["BAHNSCHRIFT.TTF", "arialbd.ttf", "arial.ttf"], 38)
    body = load_font(["BAHNSCHRIFT.TTF", "arial.ttf"], 28)
    badge = load_font(["arialbd.ttf", "arial.ttf"], 20)

    img = Image.new("RGB", (CARD_W, CARD_H), PAPER)
    draw = ImageDraw.Draw(img)

    sidebar_w = 380
    draw.rectangle([0, 0, sidebar_w, CARD_H], fill=INK_950)
    draw.rectangle([0, 0, sidebar_w, 8], fill=ACCENT)

    draw.text((48, 60), "BIG", font=display, fill=PAPER)
    draw.text((48, 200), "7", font=load_font(["impact.ttf", "arialbd.ttf"], 220), fill=ACCENT)
    draw.text((48, 470), "CONSTRUCTION", font=badge, fill=PAPER)
    draw.text((48, 500), "METRO ATLANTA", font=badge, fill=(140, 148, 156))

    text_x = sidebar_w + 60
    draw.rectangle([text_x, 60, text_x + 60, 68], fill=ACCENT)
    draw.text((text_x, 90), "GENERAL CONTRACTOR", font=badge, fill=INK_500)

    draw.text((text_x, 130), "Commercial.", font=subhead, fill=INK_950)
    draw.text((text_x, 180), "Industrial.", font=subhead, fill=INK_950)
    draw.text((text_x, 230), "Residential.", font=subhead, fill=INK_950)

    draw.line([(text_x, 310), (text_x + 500, 310)], fill=(200, 195, 185), width=2)

    draw.text((text_x, 340), "Two divisions,", font=body, fill=INK_500)
    draw.text((text_x, 378), "every trade in-house.", font=body, fill=INK_500)

    draw.text((text_x, 470), "LICENSED  ·  BONDED  ·  INSURED", font=badge, fill=BLUE)
    draw.text((text_x, 505), "Full itemized bid inside two weeks.", font=body, fill=INK_950)

    draw.rectangle([0, CARD_H - 6, CARD_W, CARD_H], fill=INK_950)

    img.save(out, "PNG", optimize=True)
    print(f"wrote {out} ({out.stat().st_size} bytes, {CARD_W}x{CARD_H})")


if __name__ == "__main__":
    main()
