"""
Build the animated Pinterest GIFs in /media from brand geometry.

    python tools/make_pins.py

Output: media/*.gif (600 x 900, 2:3) + media/pins.json. Never hand-edit the
GIFs; change this script and re-run. When a GIF changes, bump VERSION so the
file name changes (the /media folder is cached for a year).

Needs Pillow + numpy and the Inter variable font installed on this machine.
"""
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

VERSION = "v1"
W, H = 600, 900          # output size (2:3, Pinterest pin ratio)
SS = 2                   # supersampling for smooth edges
FPS = 20
SITE = "https://akdeinzmotion.com"

ROOT = Path(__file__).resolve().parents[1]                 # website/
BRAND = ROOT.parent                                        # brand assets folder
OUT = ROOT / "media"
FONT = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts\Inter-VariableFont_opsz,wght.ttf"))
WORDMARK = BRAND / "04 Wordmark" / "PNG" / "Akdeinz-Motion_Wordmark_White.png"

C = {
    "black": (0, 0, 0), "white": (255, 255, 255), "blue": (46, 107, 255),
    "aegean": (11, 53, 201), "fold": (230, 230, 230), "foldDark": (204, 204, 204),
    "carbon": (25, 25, 25), "mute": (140, 140, 140),
}
TAN60 = math.sqrt(3)
AX, AY = 0.5, math.sqrt(3) / 2


# ---------- brand easing: cubic-bezier(0.2, 0.8, 0.2, 1) ----------
def ease(x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bez = lambda t, a, b: 3 * a * t * (1 - t) ** 2 + 3 * b * t * t * (1 - t) + t ** 3
    lo, hi, t = 0.0, 1.0, x
    for _ in range(20):
        t = (lo + hi) / 2
        if bez(t, 0.2, 0.2) < x:
            lo = t
        else:
            hi = t
    return bez(t, 0.8, 1.0)


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def mix(c1, c2, a):
    return tuple(round(c1[i] + (c2[i] - c1[i]) * a) for i in range(3))


# ---------- mark geometry (master SVG, x shifted to 0) ----------
MW, MH = 557.76, 191.32
_o = 107.67
_s = lambda pts: [(pts[i] - _o, pts[i + 1]) for i in range(0, len(pts), 2)]
MARK_BANDS = [  # left -> right; first band rises to the right, others fall
    [_s([217.87, 0, 307.11, 0, 196.91, 191.32, 107.67, 191.32]),
     _s([158.38, 132.51, 267.07, 132.51, 300.95, 191.32, 158.38, 191.32])],
    [_s([313.87, 0, 224.63, 0, 334.83, 191.32, 424.07, 191.32])],
    [_s([522.06, 161.92, 432.81, 161.92, 339.56, 0, 428.8, 0])],
    [_s([555.23, 0, 465.99, 0, 576.19, 191.32, 665.43, 191.32])],
]
MARK_FOLDS = [
    (_s([555.23, 0, 521.97, 161.92, 432.81, 161.92, 465.88, 0]), ((445.85 - _o + 11, -1.79 + 11), (538.28 - _o + 11, 90.64 + 11))),
    (_s([428.94, 0, 395.68, 161.92, 324.35, 161.92, 311.36, 138.2, 339.58, 0]), ((320.15 - _o + 13, 4.42 - 13), (396.24 - _o + 13, 80.51 - 13))),
]


# ---------- drawing helpers (all coordinates in output px; scaled by SS) ----------
class Frame:
    def __init__(self, bg=C["black"]):
        self.im = Image.new("RGB", (W * SS, H * SS), bg)
        self.d = ImageDraw.Draw(self.im)

    def poly(self, pts, color):
        self.d.polygon([(x * SS, y * SS) for x, y in pts], fill=color)

    def band(self, x, y, w, h, color, lean=1):
        """Brand band: bottom-left (x, y), horizontal width w, height h, 60° sides."""
        k = h / TAN60 * lean
        self.poly([(x, y), (x + w, y), (x + w + k, y - h), (x + k, y - h)], color)

    def text(self, xy, s, size, color, weight=600, opsz=32, anchor="la", tracking=0.0):
        f = font(size * SS, weight, opsz)
        x, y = xy[0] * SS, xy[1] * SS
        if not tracking:
            self.d.text((x, y), s, font=f, fill=color, anchor=anchor)
            return
        # manual tracking (letter-spacing), only for left/right anchored captions
        total = sum(f.getlength(ch) for ch in s) + tracking * size * SS * (len(s) - 1)
        if anchor[0] == "r":
            x -= total
        for ch in s:
            self.d.text((x, y), ch, font=f, fill=color, anchor="l" + anchor[1])
            x += f.getlength(ch) + tracking * size * SS

    def paste(self, img, x, y, alpha=1.0):
        img = img.copy()
        if alpha < 1:
            a = img.getchannel("A").point(lambda v: int(v * alpha))
            img.putalpha(a)
        self.im.paste(img, (int(x * SS), int(y * SS)), img)

    def clip_region(self, box, draw_fn):
        """Run draw_fn on a layer, keep only what falls inside box (x0, y0, x1, y1)."""
        layer = Frame(bg=(0, 0, 0))
        layer.im = self.im.copy()
        layer.d = ImageDraw.Draw(layer.im)
        draw_fn(layer)
        mask = Image.new("L", self.im.size, 0)
        ImageDraw.Draw(mask).rectangle([v * SS for v in box], fill=255)
        self.im.paste(layer.im, (0, 0), mask)

    def out(self):
        return self.im.reduce(SS)


_fonts = {}


def font(px, weight, opsz):
    key = (px, weight, opsz)
    if key not in _fonts:
        f = ImageFont.truetype(str(FONT), px)
        f.set_variation_by_axes([opsz, weight])
        _fonts[key] = f
    return _fonts[key]


def wordmark(width):
    wm = Image.open(WORDMARK).convert("RGBA")
    h = round(wm.height * width / wm.width)
    return wm.resize((width * SS, h * SS), Image.LANCZOS), h


def mark_frame(fr, x0, y0, s, band_p, fold_a):
    """band_p: list of 4 values 0..1 (eased entry). Bands enter on their own 60° axis
    through the mark's own frame, fold shading fades up after."""
    box = (x0, y0, x0 + MW * s, y0 + MH * s)
    tx = lambda pts, dx, dy: [(x0 + (px + dx) * s, y0 + (py + dy) * s) for px, py in pts]

    def draw(layer):
        if fold_a > 0:
            col = mix(C["black"], C["fold"], fold_a)
            dark = mix(C["black"], C["foldDark"], fold_a)
            for pts, (a, b) in MARK_FOLDS:
                layer.poly(tx(pts, 0, 0), col)
                # darker crease, kept inside the fold polygon
                sub = Image.new("L", layer.im.size, 0)
                sd = ImageDraw.Draw(sub)
                sd.polygon([(x * SS, y * SS) for x, y in tx(pts, 0, 0)], fill=255)
                crease = Image.new("L", layer.im.size, 0)
                ImageDraw.Draw(crease).line(
                    [((x0 + a[0] * s) * SS, (y0 + a[1] * s) * SS), ((x0 + b[0] * s) * SS, (y0 + b[1] * s) * SS)],
                    fill=255, width=int(30 * s * SS))
                m = Image.fromarray(np.minimum(np.array(sub), np.array(crease)))
                layer.im.paste(dark, (0, 0, *layer.im.size), m)
        for i, group in enumerate(MARK_BANDS):
            d = (1 - band_p[i]) * -260
            dx, dy = d * AX, (-1 if i == 0 else 1) * d * AY
            for pts in group:
                layer.poly(tx(pts, dx, dy), C["white"])

    fr.clip_region(box, draw)


def caption(fr, y, left=None, right=None, alpha=1.0, color=C["mute"]):
    col = mix(C["black"], color, alpha)
    if left:
        fr.text((40, y), left.upper(), 13, col, weight=400, opsz=14, anchor="ls", tracking=0.12)
    if right:
        fr.text((W - 40, y), right, 15, mix(C["black"], C["white"], alpha), weight=500, opsz=14, anchor="rs")


# ---------- palette (fixed, brand-only) ----------
def build_palette():
    cols = []
    for i in range(24):
        cols.append(mix(C["black"], C["white"], i / 23))
    for base in (C["blue"], C["aegean"]):
        for i in range(1, 14):
            cols.append(mix(C["black"], base, i / 13))
        for i in range(1, 7):
            cols.append(mix(base, C["white"], i / 7))
    for i in range(1, 8):
        cols.append(mix(C["carbon"], C["blue"], i / 8))
    flat = [v for c in cols for v in c]
    flat += [0] * (768 - len(flat))
    p = Image.new("P", (1, 1))
    p.putpalette(flat)
    return p


PALETTE = build_palette()


def save(frames, name, durations=None):
    q = [f.quantize(palette=PALETTE, dither=Image.Dither.NONE) for f in frames]
    path = OUT / f"akdeinz-motion-{name}-{VERSION}.gif"
    q[0].save(path, save_all=True, append_images=q[1:], loop=0,
              duration=durations or int(1000 / FPS), optimize=True, disposal=1)
    return path


# =====================================================================
# 1. STING — the logo sting from the guidelines, then the lockup holds.
# =====================================================================
def gif_sting():
    T = 5.0
    n = int(T * FPS)
    s = 440 / MW
    mx, my = (W - MW * s) / 2, 270
    wm, wmh = wordmark(300)
    frames = []
    for f in range(n):
        t = f / FPS
        fr = Frame()
        band_p = [ease(clamp((t - 0.15 - i * 0.08) / 0.6)) for i in range(4)]
        fold_a = ease(clamp((t - 0.97) / 0.4))
        mark_frame(fr, mx, my, s, band_p, fold_a)
        # wordmark rises up the 60° axis after the bands
        a = ease(clamp((t - 1.2) / 0.5))
        off = (1 - a) * 24
        fr.paste(wm, (W - 300) / 2 + off * AX * -1, my + MH * s + 44 + off * AY, alpha=a)
        # tagline
        a2 = ease(clamp((t - 1.6) / 0.5))
        fr.text((W / 2, 610 + (1 - a2) * 14), "Movement, framed with intent.", 25, mix(C["black"], C["white"], a2),
                weight=600, opsz=32, anchor="mm")
        # cover band, bottom-left
        b = ease(clamp((t - 1.9) / 0.7))
        bw, bh = 300, 44
        x = -bw + b * bw
        fr.poly([(x - 30, H), (x + bw - bh / TAN60, H), (x + bw, H - bh), (x - 30, H - bh)], C["blue"])
        caption(fr, H - 64, right="akdeinzmotion.com", alpha=ease(clamp((t - 2.0) / 0.5)))
        frames.append(fr.out())
    return save(frames, "sting")


# =====================================================================
# 2. FIELD — bands rising on the 60° axis; seamless loop.
# =====================================================================
def gif_field():
    import random
    rnd = random.Random(7)
    T = 4.0
    n = int(T * FPS)
    top, bottom = 0, 600            # band area
    area_h = bottom - top
    palette = [C["white"]] * 3 + [C["fold"]] * 2 + [C["carbon"]] * 5 + [(42, 42, 42)] * 3 + [C["blue"]] * 2
    bands = []
    for i in range(26):
        depth = rnd.random()
        h = 70 + depth * 260
        w = (6 + rnd.random() ** 3 * 90) * (0.5 + depth)
        P = (area_h + h + 20) / AY                 # distance to cross the area fully
        k = 1 if depth < 0.6 else 2                # whole laps per loop -> seamless
        bands.append(dict(h=h, w=w, P=P, v=k * P / T, s0=rnd.random() * P,
                          x0=rnd.uniform(-area_h / TAN60, W), color=rnd.choice(palette), depth=depth))
    bands.sort(key=lambda b: b["depth"])
    wm, wmh = wordmark(220)
    frames = []
    for f in range(n):
        t = f / FPS
        fr = Frame()

        def draw(layer):
            for b in bands:
                d = (b["s0"] + b["v"] * t) % b["P"]
                x = b["x0"] + d * AX
                y = bottom + b["h"] + 10 - d * AY
                layer.band(x - (b["P"] * AX) / 2, y, b["w"], b["h"], b["color"])

        fr.clip_region((0, top, W, bottom), draw)
        fr.text((40, 700), "Movement,", 46, C["white"], weight=800, opsz=32, anchor="ls")
        fr.text((40, 752), "framed with intent.", 46, C["blue"], weight=800, opsz=32, anchor="ls")
        fr.paste(wm, 40, H - 64 - wmh + 2)
        caption(fr, H - 64 + 2, right="akdeinzmotion.com")
        frames.append(fr.out())
    return save(frames, "field")


# =====================================================================
# 3. WAVES — Akdeniz (the Mediterranean) as a swell of bands; seamless loop.
# =====================================================================
def gif_waves():
    T = 3.0
    n = int(T * FPS)
    cols, rows = 10, 9
    area = (0, 0, W, 600)
    cw, rh = W / cols, (area[3] - area[1]) / rows
    wm, wmh = wordmark(220)
    frames = []
    for f in range(n):
        t = f / FPS
        ph = 2 * math.pi * t / T
        fr = Frame()

        def draw(layer):
            for r in range(rows):
                for c in range(-1, cols + 1):
                    v = math.sin(c * 0.62 - ph + r * 0.7) * 0.5 + 0.5
                    h = rh * (0.12 + 0.8 * ease(v))
                    x = c * cw - (r % 2) * cw * 0.5
                    y = area[1] + (r + 1) * rh
                    layer.band(x, y, cw * 0.3, h, C["blue"] if v > 0.93 else C["white"])

        fr.clip_region(area, draw)
        fr.text((40, 690), "Sharp coastlines,", 40, C["white"], weight=800, opsz=32, anchor="ls")
        fr.text((40, 736), "waves, sun on water.", 40, C["white"], weight=800, opsz=32, anchor="ls")
        fr.paste(wm, 40, H - 64 - wmh + 2)
        caption(fr, H - 64 + 2, right="akdeinzmotion.com")
        frames.append(fr.out())
    return save(frames, "waves")


# ---------- shared layout for the text pins ----------
AREA = (0, 0, W, 600)


def text_block(fr, lines, wm, wmh, size=44):
    """Headline lines (text, colour) in the bottom third, then wordmark + URL."""
    step = round(size * 1.12)
    y = min(690, 756 - (len(lines) - 1) * step)   # longer headlines start higher
    for txt, col in lines:
        fr.text((40, y), txt, size, col, weight=800, opsz=32, anchor="ls")
        y += step
    fr.paste(wm, 40, H - 64 - wmh + 2)
    caption(fr, H - 64 + 2, right="akdeinzmotion.com")


# =====================================================================
# 4. AXIS — slats breathing on the 60° axis. Guideline: "Move on the 60° axis"
# =====================================================================
def gif_axis():
    T = 3.0
    n = int(T * FPS)
    wm, wmh = wordmark(220)
    nslat = 12
    step = (W + 600 / TAN60) / nslat
    frames = []
    for f in range(n):
        t = f / FPS
        ph = 2 * math.pi * t / T
        fr = Frame()

        def draw(layer):
            drift = (t / T) * step                    # one slat per loop -> seamless
            for i in range(-2, nslat + 2):
                v = 0.5 + 0.5 * math.sin(ph - i * 0.55)
                w = step * (0.1 + 0.45 * v)
                x = i * step - 600 / TAN60 + drift
                layer.band(x, 600, w, 600, C["blue"] if i % 6 == 2 else C["white"])

        fr.clip_region(AREA, draw)
        text_block(fr, [("Move on", C["white"]), ("the 60° axis.", C["blue"])], wm, wmh, 52)
        frames.append(fr.out())
    return save(frames, "axis")


# =====================================================================
# 5. FOLD — a ribbon pulled through a frame; past the edge it folds.
#    Guideline: "Reveal with the fold"
# =====================================================================
def gif_fold():
    T = 4.0
    n = int(T * FPS)
    wm, wmh = wordmark(220)
    edge = W * 0.55
    bh, bw = 640, 96
    travel = W + bh / TAN60 + bw
    frames = []
    for f in range(n):
        t = f / FPS
        fr = Frame(bg=C["carbon"])
        xs = [-bw - bh / TAN60 + ((t / T + i / 4) % 1) * travel for i in range(4)]

        def draw_left(layer):
            for x in xs:
                layer.band(x, 620, bw, bh, C["white"])

        def draw_right(layer):
            for x in xs:
                layer.band(2 * edge - x - bw, 620, bw, bh, C["fold"], lean=-1)
            layer.band(edge, 620, 14, bh, C["foldDark"], lean=-1)

        fr.clip_region((0, 0, edge, 600), draw_left)
        fr.clip_region((edge, 0, W, 600), draw_right)
        fr.poly([(0, 600), (W, 600), (W, H), (0, H)], C["black"])
        text_block(fr, [("Reveal", C["white"]), ("with the fold.", C["white"])], wm, wmh, 52)
        frames.append(fr.out())
    return save(frames, "fold")


# =====================================================================
# 6. EASING — bands arrive on one curve, 80 ms apart, hold, leave.
#    Guideline: "One easing"
# =====================================================================
def gif_easing():
    T = 3.6
    n = int(T * FPS)
    wm, wmh = wordmark(220)
    rows, bh = 6, 64
    frames = []
    for f in range(n):
        t = f / FPS
        fr = Frame()

        def draw(layer):
            for i in range(rows):
                tin = ease(clamp((t - 0.2 - i * 0.08) / 0.6))
                tout = ease(clamp((t - 2.6 - i * 0.08) / 0.3))
                w = 300 + i * 22
                y = 120 + i * (bh + 18) + bh
                d = (1 - tin) * -900 + tout * 900          # travel along the 60° axis
                layer.band(60 + d * AX, y - d * AY, w, bh, C["blue"] if i == rows - 1 else C["white"])

        fr.clip_region(AREA, draw)
        text_block(fr, [("One easing.", C["white"])], wm, wmh, 56)
        fr.text((40, 742), "cubic-bezier(0.2, 0.8, 0.2, 1)", 17, C["mute"], weight=400, opsz=14, anchor="ls")
        frames.append(fr.out())
    return save(frames, "easing")


# =====================================================================
# 7. CLIMB — bars stack upward on the 60° offset, hold, clear.
#    Guideline: "Akdeinz Motion rises on 60° and climbs."
# =====================================================================
def gif_climb():
    T = 4.0
    n = int(T * FPS)
    wm, wmh = wordmark(220)
    k = 8
    bh = 560 / (k + 1)
    widths = [0.62, 0.48, 0.56, 0.4, 0.5, 0.36, 0.44, 0.3]
    frames = []
    for f in range(n):
        t = f / FPS
        fr = Frame()

        def draw(layer):
            for i in range(k):
                tin = ease(clamp((t - 0.1 - i * 0.12) / 0.55))
                tout = ease(clamp((t - 3.1 - (k - i) * 0.04) / 0.3))
                d = (1 - tin) * -700 + tout * 700
                layer.band(40 + i * bh / TAN60 + d * AX, 590 - bh * i - d * AY, W * widths[i], bh * 0.8,
                           C["blue"] if i == k - 1 else C["white"])

        fr.clip_region(AREA, draw)
        text_block(fr, [("Rises on 60°", C["white"]), ("and climbs.", C["blue"])], wm, wmh, 52)
        frames.append(fr.out())
    return save(frames, "climb")


# =====================================================================
# 8. GEOMETRY — nested bands receding into the frame; seamless loop.
#    Guideline: "flat geometry, angled cuts, no gradients, no ornament"
# =====================================================================
def gif_geometry():
    T = 3.0
    n = int(T * FPS)
    wm, wmh = wordmark(220)
    cx, cy, ratio = W / 2, 300, 1.32
    frames = []
    for f in range(n):
        t = f / FPS
        fr = Frame()
        ph = t / T                    # grows by one ring per loop; colours swap each ring -> two loops per cycle

        def draw(layer):
            for kk in range(18, -1, -1):
                sc = ratio ** (kk - 2 * ph) * 14
                h, w = sc * 1.6, sc * 1.1
                layer.band(cx - w / 2 - h / TAN60 / 2, cy + h / 2, w, h, C["white"] if kk % 2 == 0 else C["black"])

        fr.clip_region(AREA, draw)
        text_block(fr, [("Flat geometry.", C["white"]), ("Angled cuts.", C["white"]), ("No ornament.", C["blue"])], wm, wmh, 44)
        frames.append(fr.out())
    return save(frames, "geometry")


# ---------- manifest for the Pinterest automation ----------
PINS = {
    "sting": dict(
        title="Akdeinz Motion — Movement, framed with intent",
        description="The Akdeinz Motion mark: an A and an M joined into one form, built from bands cut at 60°. Motion design studio, an East Marketing brand.",
        alt="White Akdeinz Motion logo animating in on a black background, with the tagline Movement, framed with intent, and a blue band.",
    ),
    "field": dict(
        title="Movement, framed with intent — Akdeinz Motion",
        description="Bands rising on a single 60° axis, the motion system behind the Akdeinz Motion identity.",
        alt="White, grey and blue parallelogram bands rising diagonally across a black background above the words Movement, framed with intent.",
    ),
    "waves": dict(
        title="Sharp coastlines, waves, sun on water — Akdeinz Motion",
        description="Akdeniz is the Mediterranean, kept abstract and geometric. A study in 60° bands by Akdeinz Motion.",
        alt="Rows of white and blue slanted bands rising and falling like waves on a black background.",
    ),
    "axis": dict(
        title="Move on the 60° axis — Akdeinz Motion",
        description="Bands enter and exit along their own diagonal. A motion principle of the Akdeinz Motion identity.",
        alt="White and blue slanted bands widening and narrowing in a wave on a black background, above the words Move on the 60° axis.",
    ),
    "fold": dict(
        title="Reveal with the fold — Akdeinz Motion",
        description="Where the bands overlap, a soft fold catches the light, like film or ribbon pulled through a frame.",
        alt="White bands sliding across a dark frame and turning light grey where they fold at an edge, above the words Reveal with the fold.",
    ),
    "easing": dict(
        title="One easing — Akdeinz Motion",
        description="Every Akdeinz Motion animation uses one curve: cubic-bezier(0.2, 0.8, 0.2, 1).",
        alt="Six slanted bands sliding in one after another, holding, then sliding out, above the words One easing.",
    ),
    "climb": dict(
        title="Rises on 60° and climbs — Akdeinz Motion",
        description="A sister brand to East Marketing, same family, different direction: Akdeinz Motion rises on 60° and climbs.",
        alt="Slanted white bars stacking upward like a staircase, the top one blue, above the words Rises on 60° and climbs.",
    ),
    "geometry": dict(
        title="Flat geometry. Angled cuts. No ornament. — Akdeinz Motion",
        description="The Akdeinz Motion identity: flat geometry, angled cuts, no gradients, no ornament.",
        alt="Nested black and white slanted shapes moving into the frame like a tunnel, above the words Flat geometry, angled cuts, no ornament.",
    ),
}


def main():
    OUT.mkdir(exist_ok=True)
    made = {
        "sting": gif_sting(), "field": gif_field(), "waves": gif_waves(),
        "axis": gif_axis(), "fold": gif_fold(), "easing": gif_easing(),
        "climb": gif_climb(), "geometry": gif_geometry(),
    }
    manifest = {
        "_readme": "Animated pins for the Pinterest automation. Files are hosted on the site but not loaded by any page.",
        "link": f"{SITE}/?utm_source=pinterest&utm_medium=social",
        "pins": [],
    }
    for key, path in made.items():
        manifest["pins"].append(dict(
            id=key,
            image_url=f"{SITE}/media/{path.name}",
            width=W, height=H, format="gif",
            bytes=path.stat().st_size,
            **PINS[key],
        ))
        print(f"{path.name}: {path.stat().st_size / 1024:.0f} KB")
    (OUT / "pins.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
