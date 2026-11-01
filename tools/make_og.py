"""Makes one 1200×630 social image per page into assets/og/. build_pages.py picks them up by page path.

    python tools/make_og.py

Needs Pillow and the Inter variable font (same as make_pins.py). Page titles come from content/*.json.
Re-run it when a title changes. Work pieces with a poster get the poster on the right.
"""
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRAND_MARK = ROOT.parent / "03 Mark" / "PNG" / "Akdeinz-Motion_Mark_White.png"
FONT = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts\Inter-VariableFont_opsz,wght.ttf"))
W, H = 1200, 630
BLUE = (46, 107, 255)


def font(size, weight=700):
    f = ImageFont.truetype(str(FONT), size)
    try:
        f.set_variation_by_axes([32 if size > 32 else 14, weight])
    except Exception:
        pass
    return f


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def card(name, kicker, title, poster=None):
    im = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(im)
    left_w = 640 if poster else 1000
    if poster:
        p = Image.open(ROOT / poster.lstrip("/")).convert("RGB")
        p = p.resize((round(p.width * H / p.height), H), Image.LANCZOS)
        im.paste(p, (W - p.width, 0))
        left_w = W - p.width - 110
    d.polygon([(0, 0), (14, 0), (14 - 14 * 0, H), (0, H)], fill=BLUE)  # blue edge band
    mark = Image.open(BRAND_MARK).convert("RGBA")
    mark.thumbnail((150, 80))
    im.paste(mark, (70, 60), mark)
    d.text((70, 170), kicker.upper(), font=font(22, 600), fill=BLUE)
    size = 64
    while True:
        f = font(size, 700)
        lines = wrap(d, title, f, left_w)
        if len(lines) * size * 1.12 <= 300 or size <= 36:
            break
        size -= 4
    y = 215
    for line in lines:
        d.text((70, y), line, font=f, fill=(255, 255, 255))
        y += int(size * 1.12)
    d.text((70, H - 70), "akdeinzmotion.com", font=font(24, 500), fill=(170, 170, 170))
    out = ROOT / "assets" / "og"
    out.mkdir(parents=True, exist_ok=True)
    im.save(out / f"{name}.jpg", quality=86, optimize=True)


def main():
    site = json.loads((ROOT / "content" / "site.json").read_text(encoding="utf-8"))
    card("home", "Motion design", "Your time is valuable. Let me take care of it.")
    card("work", "Selected work", "Work")
    card("reels", "Reels", "Showreel and short pieces")
    card("pricing", "Pricing", "Motion design from €390, in EUR excl. VAT")
    card("guides", "Guides", "Motion design guides for founders and small brands")
    card("about", "About", f"Akdeinz Motion. {site['person']['name']}, {site['person']['jobTitle']}.")
    card("contact", "Contact", "Get a fixed-price quote")
    for f in sorted((ROOT / "content" / "guides").glob("*.json")):
        g = json.loads(f.read_text(encoding="utf-8"))
        card(f"guides-{g['slug']}", "Guide", g["title"])
    for p in json.loads((ROOT / "content" / "projects.json").read_text(encoding="utf-8"))["projects"]:
        if p["kind"] == "work" and p.get("poster") and p.get("what") and p.get("why"):
            card(f"work-{p['slug']}", "Spec piece", p["title"], p["poster"])
    print("OG images:", len(list((ROOT / "assets" / "og").glob("*.jpg"))))


if __name__ == "__main__":
    main()
