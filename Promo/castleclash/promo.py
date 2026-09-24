"""Castle Clash promo compositor: box-art cold open + Blender shot frames + trailer titles + score/SFX -> 1280x720 H.264.

  uv run --with pillow --with numpy promo.py [out.mp4]              full 45 s video
  PREVIEW=2.5,7,16 uv run --with pillow --with numpy promo.py       dump build/preview_<t>.png stills instead

Inputs: build/edl.json + build/timeline.json (sim.py), build/frames/*.png + build/frame_meta.json (scene.py),
build/boxart.png (the cartridge-box painting), sfx/ (gen_audio.cjs) and the Lens' own cues in Assets/GeneratedSFX.
"""
import json, math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
FRAMES = os.path.join(BUILD, "frames")
LENS_SFX = os.path.abspath(os.path.join(HERE, "../../Assets/GeneratedSFX"))
SFX = os.path.join(HERE, "sfx")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "CastleClash_Promo_720p.mp4")
PREVIEW = os.environ.get("PREVIEW")

W, H, FPS = 1280, 720, 30
EDL = json.load(open(os.path.join(BUILD, "edl.json")))
TL = json.load(open(os.path.join(BUILD, "timeline.json")))
FMETA = json.load(open(os.path.join(BUILD, "frame_meta.json"))) if os.path.exists(os.path.join(BUILD, "frame_meta.json")) else {}
DUR = EDL["duration"]
NF = int(DUR * FPS)
SHOTS = EDL["shots"]
SHOT = {s["id"]: s for s in SHOTS}
BOX0, BOX1 = EDL["box"]["v0"], EDL["box"]["v1"]
CTA0 = EDL["cta"]["v0"]
IMPACT_V = 36.0                     # the crown impact sits on the score's downbeat (see sim.py)

TEAL, AMBER = (26, 242, 224), (255, 158, 31)
FIRE1, FIRE2, FIRE3 = (255, 236, 150), (255, 140, 30), (200, 30, 10)
WHITE, BLACK = (255, 255, 255), (0, 0, 0)

SUP = "/System/Library/Fonts/Supplemental/"
FUT = lambda s: ImageFont.truetype(SUP + "Futura.ttc", s, index=4)             # Condensed ExtraBold
HEAVY = lambda s: ImageFont.truetype("/System/Library/Fonts/Avenir Next Condensed.ttc", s, index=8)
HEAVY_I = lambda s: ImageFont.truetype("/System/Library/Fonts/Avenir Next Condensed.ttc", s, index=9)
DEMI = lambda s: ImageFont.truetype("/System/Library/Fonts/Avenir Next Condensed.ttc", s, index=2)
ROCK = lambda s: ImageFont.truetype(SUP + "Rockwell.ttc", s, index=2)


def clamp01(x):
    return max(0.0, min(1.0, x))


def smooth(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def ease_out(x, p=3):
    return 1 - (1 - clamp01(x)) ** p


def back_out(x, k=1.8):
    x = clamp01(x) - 1
    return 1 + (k + 1) * x ** 3 + k * x ** 2


# ---------------------------------------------------------------- shot <-> sim time
def sim_time(sh, v):
    m = sh["map"]
    if v <= m[0][0]:
        return m[0][1]
    for (va, sa), (vb, sb) in zip(m, m[1:]):
        if va <= v <= vb:
            return sa + (sb - sa) * (v - va) / (vb - va)
    return m[-1][1]


def video_time(sh, t):
    m = sh["map"]
    for (va, sa), (vb, sb) in zip(m, m[1:]):
        if sa <= t <= sb and sb > sa:
            return va + (vb - va) * (t - sa) / (sb - sa)
    return None


def events_in(sh, kinds):
    seg = TL[sh["seg"]]["events"]
    lo, hi = sh["map"][0][1], sh["map"][-1][1]
    out = []
    for e in seg:
        if e["kind"] in kinds and lo <= e["t"] < hi:
            v = video_time(sh, e["t"])
            if v is not None and sh["v0"] <= v < sh["v1"]:
                out.append((v, e))
    return out


def shot_at(t):
    for s in SHOTS:
        if s["v0"] <= t < s["v1"]:
            return s
    return None


# ---------------------------------------------------------------- text rendering (cached sprites)
_cache = {}


def text_sprite(text, font, size, fill=WHITE, stroke=0, stroke_fill=BLACK, tracking=0, shadow=True, glow=None):
    key = (text, font, size, fill, stroke, stroke_fill, tracking, shadow, glow)
    if key in _cache:
        return _cache[key]
    f = font(size)
    widths = [f.getbbox(ch, stroke_width=stroke)[2] - f.getbbox(ch, stroke_width=stroke)[0] if ch != " " else size * 0.28 for ch in text]
    adv = [f.getlength(ch) + tracking for ch in text]
    tw = int(sum(adv) + stroke * 2 + 40)
    asc, desc = f.getmetrics()
    th = asc + desc + stroke * 2 + 40
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 20 + stroke
    for ch, a in zip(text, adv):
        d.text((x, 20 + stroke), ch, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
        x += a
    im = im.crop(im.getbbox())
    pad = 30
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    if glow:
        g = Image.new("RGBA", out.size, (0, 0, 0, 0))
        g.paste(Image.new("RGBA", im.size, glow + (255,)), (pad, pad), im)
        out.alpha_composite(g.filter(ImageFilter.GaussianBlur(10)))
        out.alpha_composite(g.filter(ImageFilter.GaussianBlur(4)))
    if shadow:
        s = Image.new("RGBA", out.size, (0, 0, 0, 0))
        s.paste(Image.new("RGBA", im.size, (0, 0, 0, 170)), (pad + 3, pad + 5), im)
        out.alpha_composite(s.filter(ImageFilter.GaussianBlur(6)))
    out.alpha_composite(im, (pad, pad))
    _cache[key] = out
    return out


def place(img, spr, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if scale <= 0.01 or alpha <= 0.01:
        return
    s = spr
    if abs(scale - 1) > 0.005:
        s = s.resize((max(1, int(s.width * scale)), max(1, int(s.height * scale))), Image.LANCZOS if scale < 1 else Image.BICUBIC)
    if abs(rot) > 0.05:
        s = s.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 0.999:
        s = s.copy()
        s.putalpha(s.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))


def title_in(img, t, t0, t1, spr, cx, cy, mode="punch"):
    """Trailer title: punch in (scale from 1.35 + blur-free), hold with slow drift, fade out."""
    if not (t0 <= t < t1):
        return
    u = t - t0
    k_in = ease_out(u / 0.22)
    out = 1 - smooth((t - (t1 - 0.25)) / 0.25)
    if mode == "punch":
        sc = 1.32 - 0.32 * k_in + 0.025 * u
    elif mode == "rise":
        sc = 1.0 + 0.02 * u
        cy += 24 * (1 - k_in)
    else:
        sc = 1.0
    place(img, spr, cx, cy, sc, k_in * out)


def logo_sprite(size=170):
    """Retro cartridge logo: extruded italic block letters with a fire gradient face and dark outline."""
    key = ("logo", size)
    if key in _cache:
        return _cache[key]
    f = FUT(size)
    lines = ["CASTLE", "CLASH"]
    lw = [f.getlength(l) + 10 * len(l) for l in lines]
    Wd, Hd = int(max(lw) + 160), int(size * 2.15 + 140)
    face = Image.new("L", (Wd, Hd), 0)
    d = ImageDraw.Draw(face)
    y = 50
    for l, w in zip(lines, lw):
        x = (Wd - w) / 2
        for ch in l:
            d.text((x, y), ch, font=f, fill=255)
            x += f.getlength(ch) + 10
        y += int(size * 1.02)
    # italic shear
    sh = 0.22
    face = face.transform(face.size, Image.AFFINE, (1, sh, -sh * Hd / 2, 0, 1, 0), resample=Image.BICUBIC)
    out = Image.new("RGBA", face.size, (0, 0, 0, 0))
    # extrusion: dark red to black, stepping down-right
    for i in range(14, 0, -1):
        c = (int(90 - 5 * i), int(12), int(8), 255)
        layer = Image.new("RGBA", face.size, c)
        out.paste(layer, (i, i), face)
    outline = face.filter(ImageFilter.MaxFilter(9))
    out.paste(Image.new("RGBA", face.size, (40, 6, 4, 255)), (0, 0), outline)
    # vertical fire gradient face with a hot highlight band
    grad = np.zeros((Hd, Wd, 4), np.uint8)
    ys = np.linspace(0, 1, Hd)[:, None]
    for c, (a, b, cc) in enumerate(zip(FIRE1, FIRE2, FIRE3)):
        top = a + (b - a) * np.clip(ys * 2.2, 0, 1)
        grad[..., c] = np.clip(np.where(ys < 0.45, top, b + (cc - b) * np.clip((ys - 0.45) * 2.2, 0, 1)), 0, 255).astype(np.uint8)
    grad[..., 3] = 255
    band = ((np.abs(((np.arange(Hd)[:, None] - 50) % (size * 1.02)) / (size * 1.02) - 0.42) < 0.05) * 60).astype(np.int16)
    grad[..., :3] = np.clip(grad[..., :3].astype(np.int16) + band[..., None], 0, 255).astype(np.uint8)
    out.paste(Image.fromarray(grad, "RGBA"), (0, 0), face)
    # inner white hairline for that printed-box sheen
    inner = face.filter(ImageFilter.MinFilter(5))
    edge = ImageChops.subtract(face, inner)
    out.paste(Image.new("RGBA", face.size, (255, 250, 220, 150)), (0, 0), edge)
    out = out.crop(out.getbbox())
    _cache[key] = out
    return out


# ---------------------------------------------------------------- the box art
def load_boxart():
    p = os.path.join(BUILD, "boxart.png")
    if os.path.exists(p):
        return Image.open(p).convert("RGB")
    # placeholder until the painting exists: smouldering gradient
    im = Image.new("RGB", (1024, 1024))
    a = np.zeros((1024, 1024, 3), np.uint8)
    yy = np.linspace(0, 1, 1024)[:, None]
    a[..., 0] = (60 + 160 * yy).astype(np.uint8)
    a[..., 1] = (20 + 60 * yy).astype(np.uint8)
    a[..., 2] = 18
    return Image.fromarray(a)


BOXART = load_boxart()


def art_crop(zoom, cx=0.5, cy=0.46):
    """16:9 window into the painting; zoom 1 = widest 16:9 crop."""
    aw, ah = BOXART.size
    cw = min(aw, ah * 16 / 9) / zoom
    ch = cw * 9 / 16
    x0 = clamp01(cx - cw / aw / 2) * aw
    y0 = clamp01(cy - ch / ah / 2) * ah
    x0, y0 = min(x0, aw - cw), min(y0, ah - ch)
    return BOXART.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BICUBIC)


def box_face(w=560):
    """The cartridge box front: black frame, hot diagonal stripe band, the painting, logo and tag lines."""
    key = ("box", w)
    if key in _cache:
        return _cache[key]
    h = int(w * 1.32)
    im = Image.new("RGBA", (w, h), (10, 10, 12, 255))
    d = ImageDraw.Draw(im)
    band_y = int(h * 0.075)
    for i, c in enumerate([(255, 214, 64), (255, 150, 28), (236, 72, 22), (170, 24, 18)]):
        d.polygon([(0, band_y + i * 9), (w, band_y - 40 + i * 9), (w, band_y - 32 + i * 9), (0, band_y + 8 + i * 9)], fill=c)
    art_h = int(h * 0.62)
    art = BOXART.copy()
    aw, ah = art.size
    tw, th = w - 36, art_h
    s = max(tw / aw, th / ah)
    art = art.resize((int(aw * s), int(ah * s)), Image.LANCZOS)
    art = art.crop(((art.width - tw) // 2, (art.height - th) // 2, (art.width - tw) // 2 + tw, (art.height - th) // 2 + th))
    im.paste(art, (18, int(h * 0.15)))
    d.rectangle((18, int(h * 0.15), 18 + tw, int(h * 0.15) + th), outline=(255, 150, 28), width=3)
    logo = logo_sprite(92)
    lw = int(w * 0.86)
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    im.alpha_composite(logo, ((w - lw) // 2, int(h * 0.15) + th - logo.height // 2 - 6))
    tag = text_sprite("TABLETOP AR  ·  1 OR 2 PLAYERS", ROCK, 24, (255, 214, 64), shadow=False, tracking=2)
    im.alpha_composite(tag, ((w - tag.width) // 2, h - 88))
    tag2 = text_sprite("A LENS FOR SPECS", HEAVY, 30, WHITE, shadow=False, tracking=5)
    im.alpha_composite(tag2, ((w - tag2.width) // 2, h - 56))
    _cache[key] = im
    return im


def perspective(img, tilt_y, tilt_x=0.0):
    """Cheap 3D card tilt: squeeze one side (tilt_y in -1..1), then mild vertical keystone."""
    w, h = img.size
    k = 0.10 * tilt_y
    kx = 0.06 * tilt_x
    quad = (0 + w * max(0, kx), h * max(0, k),                   # upper-left
            0, h - h * max(0, k),                                 # lower-left
            w, h - h * max(0, -k),                                # lower-right
            w - w * max(0, kx), h * max(0, -k))                   # upper-right
    return img.transform(img.size, Image.QUAD, quad, resample=Image.BICUBIC)


# ---------------------------------------------------------------- particles: embers + sparks overlay (2D)
EMB = random.Random(9)
EMBERS = [(EMB.uniform(0, W), EMB.uniform(0, H), EMB.uniform(-30, 30), EMB.uniform(60, 190), EMB.uniform(1.2, 3.6), EMB.uniform(0, 6))
          for _ in range(140)]


def embers(img, t, strength=1.0, t0=0.0):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x, y, vx, vy, r, ph in EMBERS:
        tt = t - t0
        px = (x + vx * tt + 26 * math.sin(tt * 1.7 + ph)) % W
        py = (y - vy * tt) % (H + 60) - 30
        flick = 0.55 + 0.45 * math.sin(tt * 9 + ph * 3)
        a = int(255 * strength * flick)
        c = (255, int(150 + 80 * flick), 60, a)
        d.ellipse((px - r, py - r, px + r, py + r), fill=c)
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.8)))
    glow = layer.filter(ImageFilter.GaussianBlur(6))
    img.alpha_composite(glow)


# ---------------------------------------------------------------- grading
def grade(img, bloom=0.55, vignette=0.55, grain=0.016, warm=0.0, red=0.0, seed=0):
    a = np.asarray(img.convert("RGB")).astype(np.float32) / 255.0
    # bloom: soft threshold -> wide + tight blur
    lum = a.max(axis=2, keepdims=True)
    bright = a * np.clip((lum - 0.72) / 0.28, 0, 1)
    b8 = Image.fromarray((bright * 255).astype(np.uint8))
    wide = np.asarray(b8.filter(ImageFilter.GaussianBlur(18))).astype(np.float32) / 255
    tight = np.asarray(b8.filter(ImageFilter.GaussianBlur(5))).astype(np.float32) / 255
    a = a + bloom * (0.9 * wide + 0.6 * tight)
    # teal/orange split: warm highlights, cool shadows
    l = a.mean(axis=2, keepdims=True)
    a = a + (np.array([0.05, 0.015, -0.03]) * np.clip(l - 0.35, 0, 1) + np.array([-0.012, 0.004, 0.02]) * np.clip(0.4 - l, 0, 1)) * (1 + warm)
    if red:
        a = a * (1 - 0.35 * red) + np.array([0.28, 0.02, 0.0]) * red * l
    # vignette
    yy, xx = np.mgrid[0:H, 0:W]
    v = ((xx - W / 2) / (W / 2)) ** 2 * 0.8 + ((yy - H / 2) / (H / 2)) ** 2
    a *= (1 - vignette * 0.45 * np.clip(v - 0.25, 0, 1.5))[..., None]
    # filmic shoulder + grain
    a = a / (1 + 0.18 * a)
    a *= 1.18
    rng = np.random.default_rng(seed)
    a += rng.normal(0, grain, (H, W, 1)).astype(np.float32)
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")


# ---------------------------------------------------------------- per-shot overlays
def shake(img, t, hits, amp=16, decay=10):
    ox = oy = 0.0
    z = 1.0
    for tb, k in hits:
        if 0 <= t - tb < 0.5:
            e = math.exp(-decay * (t - tb)) * k
            ox += amp * e * math.sin(t * 97)
            oy += amp * 0.8 * e * math.cos(t * 83)
            z += 0.05 * e
    if abs(ox) + abs(oy) < 0.3 and z < 1.001:
        return img
    cw, ch = W / z, H / z
    cx, cy = W / 2 + ox, H / 2 + oy
    return img.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((W, H), Image.BICUBIC)


def flash(img, a, color=(255, 240, 210)):
    if a > 0.005:
        img.alpha_composite(Image.new("RGBA", (W, H), color + (int(255 * clamp01(a)),)))


def lower_third(img, t, t0, t1, title, sub, color):
    if not (t0 <= t < t1):
        return
    k = ease_out((t - t0) / 0.35)
    out = 1 - smooth((t - (t1 - 0.3)) / 0.3)
    a = k * out
    x = 70 - 40 * (1 - k)
    bar = Image.new("RGBA", (6, 96), color + (int(255 * a),))
    img.alpha_composite(bar, (int(x) - 22, 548))
    s1 = text_sprite(title, HEAVY, 66, WHITE, tracking=2)
    s2 = text_sprite(sub, DEMI, 30, color, tracking=1)
    place(img, s1, x + s1.width / 2 - 30, 575, 1.0, a)
    place(img, s2, x + s2.width / 2 - 30, 628, 1.0, a)


def specs_frame(img, t, a=1.0):
    """Subtle 'through the glasses' framing: soft rounded viewport edge + corner ticks."""
    if a <= 0:
        return
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c = (200, 235, 255, int(150 * a))
    m, L = 38, 46
    for (x, y, sx, sy) in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        d.line((x, y, x + sx * L, y), fill=c, width=3)
        d.line((x, y, x, y + sy * L), fill=c, width=3)
    lbl = text_sprite("SPECS  ·  LIVE", DEMI, 22, (200, 235, 255), shadow=False, tracking=4)
    layer.alpha_composite(lbl, (m + 12, m + 6))
    dot = int(255 * a * (0.5 + 0.5 * math.sin(t * 5)))
    d.ellipse((m + 2, m + 18, m + 12, m + 28), fill=(255, 70, 60, dot))
    img.alpha_composite(layer)


def feature_card(img, t, t0, t1):
    feats = [("HAND-TRACKED CONTROL", "pinch & slide your shield"),
             ("SOLO VS CPU", "starts instantly, no session"),
             ("FACE-TO-FACE MULTIPLAYER", "colocated with Spectacles Sync Kit"),
             ("WORLD-ANCHORED TABLETOP", "your table, your battlefield"),
             ("FIRST TO TWO CROWNS", "three-minute matches")]
    if not (t0 <= t < t1):
        return
    u = t - t0
    out = 1 - smooth((t - (t1 - 0.35)) / 0.35)
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(panel)
    k = ease_out(u / 0.4)
    dd.rectangle((0, 0, int(560 * k), H), fill=(6, 10, 18, int(170 * out)))
    img.alpha_composite(panel)
    head = text_sprite("BUILT FOR", DEMI, 34, (180, 220, 255), tracking=8)
    big = text_sprite("SPECS 27", HEAVY, 108, WHITE, tracking=4, glow=(90, 190, 255))
    place(img, head, 80 + head.width / 2 - 30, 98, 1.0, k * out)
    place(img, big, 80 + big.width / 2 - 30, 168, 1.0, ease_out((u - 0.1) / 0.3) * out)
    for i, (a_, b_) in enumerate(feats):
        ti = 0.55 + i * 0.32
        kk = ease_out((u - ti) / 0.3) * out
        if kk <= 0:
            continue
        y = 268 + i * 78
        s1 = text_sprite(a_, HEAVY, 36, WHITE, tracking=2)
        s2 = text_sprite(b_, DEMI, 24, (255, 190, 90))
        dot = Image.new("RGBA", (14, 14), (0, 0, 0, 0))
        ImageDraw.Draw(dot).ellipse((0, 0, 13, 13), fill=(255, 158, 31, int(255 * kk)))
        img.alpha_composite(dot, (int(84 - 30 * (1 - kk)), y - 6))
        place(img, s1, 112 + s1.width / 2 - 30 - 30 * (1 - kk), y, 1.0, kk)
        place(img, s2, 112 + s2.width / 2 - 30 - 30 * (1 - kk), y + 34, 1.0, kk)


# ---------------------------------------------------------------- frame assembly
def load_shot_frame(sh, t):
    n = round((sh["v1"] - sh["v0"]) * FPS)
    k = min(n - 1, max(0, int((t - sh["v0"]) * FPS + 1e-6)))
    key = f"{sh['id']}_{k:04d}"
    p = os.path.join(FRAMES, key + ".png")
    if os.path.exists(p):
        im = Image.open(p).convert("RGBA")
    else:
        still = os.path.join(BUILD, f"still_{sh['id']}.png")
        im = Image.open(still).convert("RGBA") if os.path.exists(still) else Image.new("RGBA", (W, H), (30, 20, 20, 255))
    return im, FMETA.get(key, {})


def cold_open(t):
    """0-6 s: the painting, logo slam at 3.0, pull back to the box, fire wipe out."""
    if t < 3.0:
        z = 1.25 - 0.13 * smooth(t / 3.0)
        img = art_crop(z, 0.5 + 0.03 * math.sin(t * 0.4), 0.44).convert("RGBA")
        # heat flicker
        f = 1.0 + 0.06 * math.sin(t * 13) * math.sin(t * 7.3)
        img = Image.eval(img, lambda v: min(255, int(v * f)))
        img = grade(img, bloom=0.5, vignette=0.9, grain=0.018, seed=int(t * 30))
        embers(img, t, 0.9)
        flash(img, 1 - smooth(t / 0.6), BLACK)
        return img
    u = t - 3.0
    if u < 1.2:
        z = 1.12 - 0.04 * u
        img = art_crop(z, 0.5, 0.44).convert("RGBA")
        img = grade(img, bloom=0.6, vignette=0.9, grain=0.018, seed=int(t * 30))
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(110 * ease_out(u / 0.2)))))
        embers(img, t, 1.0)
        k = back_out(u / 0.28, 1.4)
        place(img, logo_sprite(170), W / 2, H / 2 - 10, 2.4 - 1.4 * k if u < 0.28 else 1.0 + 0.03 * u, clamp01(u / 0.12))
        flash(img, 0.85 * math.exp(-u * 9), (255, 220, 160))
        return shake(img, t, [(3.0, 1.0)], amp=22)
    # 4.2-5.4: pull back from the full painting onto the cartridge box, floating in darkness with embers
    v = u - 1.2
    k = smooth(v / 0.8)
    bg = Image.new("RGBA", (W, H), (8, 5, 5, 255))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((W / 2 - 420, H / 2 - 320, W / 2 + 420, H / 2 + 320), fill=(180, 50, 10, 120))
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90)))
    embers(bg, t, 0.8)
    box = box_face(560)
    scale = 2.2 - (2.2 - 0.72) * k
    tilt = 0.6 * (1 - k) + 0.25 * math.sin(v * 1.4)
    b = perspective(box, tilt)
    place(bg, b, W / 2 + 40 * (1 - k), H / 2 + 6, scale * (H / box.height) * 0.9, 1.0, 3 * (1 - k))
    img = grade(bg, bloom=0.5, vignette=0.8, grain=0.018, seed=int(t * 30))
    # fire wipe into the table at 5.4-6.0
    if t > 5.35:
        img.alpha_composite(fire_wipe(smooth((t - 5.35) / 0.65), t))
    return img


_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)


def fire_wipe(w_, t):
    """Flame front sweeping left to right: burnt-through region is opaque fire, the front licks and flickers."""
    edge = -260 + (W + 520) * w_
    lick = (38 * np.sin(_yy / 23 + t * 17) + 26 * np.sin(_yy / 9.5 - t * 29) + 14 * np.sin(_yy / 4.1 + t * 41))
    d = (edge + lick) - _xx                       # >0 behind the front
    heat = np.clip(d / 220, 0, 1)
    col = np.zeros((H, W, 4), np.float32)
    # front: white-hot -> yellow -> orange -> deep red far behind
    col[..., 0] = 255
    col[..., 1] = 245 - 150 * heat
    col[..., 2] = np.clip(170 - 400 * heat, 20, 255)
    alpha = np.clip(d / 26 + 0.5, 0, 1)
    tongues = np.clip(1 - np.abs(d) / 60, 0, 1) * (0.5 + 0.5 * np.sin(_yy / 6 + t * 50))
    col[..., 3] = np.clip(alpha + 0.6 * tongues, 0, 1) * 255 * (1 - 0.8 * smooth((w_ - 0.82) / 0.18))
    return Image.fromarray(col.astype(np.uint8), "RGBA").filter(ImageFilter.GaussianBlur(3))


def cta(t):
    u = t - CTA0
    art = art_crop(1.05 + 0.02 * u, 0.5, 0.45).convert("RGBA").filter(ImageFilter.GaussianBlur(7))
    art.alpha_composite(Image.new("RGBA", (W, H), (6, 3, 3, 175)))
    embers(art, t, 0.7)
    k = back_out(u / 0.35, 1.3)
    place(art, logo_sprite(150), W / 2, 270, 1.8 - 0.8 * k if u < 0.35 else 1.0 + 0.01 * u, clamp01(u / 0.15))
    s1 = text_sprite("TWO KINGDOMS.  ONE FIREBALL.", HEAVY, 44, WHITE, tracking=6)
    title_in(art, t, CTA0 + 0.55, DUR + 1, s1, W / 2, 470, "rise")
    s2 = text_sprite("A LENS FOR SPECS", DEMI, 34, (255, 190, 90), tracking=10)
    title_in(art, t, CTA0 + 0.95, DUR + 1, s2, W / 2, 530, "rise")
    img = grade(art, bloom=0.5, vignette=0.8, grain=0.016, seed=int(t * 30))
    flash(img, 0.7 * math.exp(-u * 8), (255, 220, 160))
    flash(img, smooth((t - (DUR - 0.7)) / 0.7), BLACK)
    return img


def countdown_text(img, t, sh, meta):
    """3-2-1 from the sim's own countdown clock, then FIRE! at the serve."""
    ph, clock = meta.get("phase"), meta.get("clock", 0)
    if ph == "c":
        n = max(1, math.ceil(clock - 1e-6))
        frac = n - clock
        spr = text_sprite(str(n), HEAVY, 190, WHITE, glow=(255, 150, 40))
        place(img, spr, W / 2, H / 2 - 30, 1.35 - 0.35 * ease_out(frac / 0.25), (1 - smooth((frac - 0.75) / 0.25)))
    serve = next((v for v, e in events_in(sh, {"serve"})), None)
    if serve and serve <= t < serve + 0.9:
        spr = text_sprite("FIRE!", HEAVY_I, 170, FIRE1, stroke=4, stroke_fill=(150, 30, 10), glow=(255, 110, 20))
        u = t - serve
        place(img, spr, W / 2, H / 2 - 30, 1.5 - 0.5 * ease_out(u / 0.18) + 0.1 * u, 1 - smooth((u - 0.6) / 0.3))


def shot_frame(sh, t):
    img, meta = load_shot_frame(sh, t)
    sid = sh["id"]
    u = t - sh["v0"]
    hits = [(v, 0.35) for v, e in events_in(sh, {"shield"})] + [(v, 0.8 if e["hp"] == 0 else 0.5) for v, e in events_in(sh, {"stone"})]
    hits += [(v, 1.0) for v, e in events_in(sh, {"win"})] + [(v, 0.4) for v, e in events_in(sh, {"sudden"})]
    img = shake(img, t, hits, amp=10, decay=12)
    red = 0.0
    if sid == "sudden":
        red = 0.35 + 0.15 * math.sin(t * 6)
    if sid == "crown":
        red = 0.2 * (1 - smooth((t - IMPACT_V) / 1.0))
    img = grade(img, bloom=0.42 if sid != "crown" else 0.16, vignette=0.6 if sid != "crown" else 0.85, red=red, seed=int(t * 30))
    # flashes on big moments
    for v, e in events_in(sh, {"stone"}):
        if e["hp"] == 0:
            flash(img, 0.22 * math.exp(-(t - v) * 14) if t >= v else 0, (255, 190, 120))
    for v, e in events_in(sh, {"win"}):
        flash(img, 0.8 * math.exp(-(t - v) * 9) if t >= v else 0, (255, 235, 200))

    if sid == "reveal":
        specs_frame(img, t, smooth(u / 0.6) * (1 - smooth((u - 3.4) / 0.5)))
        title_in(img, t, sh["v0"] + 0.5, sh["v0"] + 2.2, text_sprite("YOUR TABLE", HEAVY, 92, WHITE, tracking=8), W / 2, 150)
        title_in(img, t, sh["v0"] + 2.0, sh["v1"], text_sprite("BECOMES A BATTLEFIELD", HEAVY, 92, WHITE, tracking=8), W / 2, 150)
    elif sid == "serve":
        countdown_text(img, t, sh, meta)
    elif sid == "rally":
        words = ["DEFLECT", "RICOCHET", "ACCELERATE", "DEFEND"]
        sv = [v for v, e in events_in(sh, {"shield"})]
        for i, v in enumerate(sv[:4]):
            nxt = sv[i + 1] if i + 1 < len(sv) else sh["v1"]
            title_in(img, t, v, min(nxt, v + 1.4, sh["v1"]), text_sprite(words[i], HEAVY_I, 110, WHITE, tracking=6, glow=TEAL if i % 2 == 0 else AMBER),
                     W / 2, 130)
    elif sid == "walls":
        title_in(img, t, sh["v0"] + 0.15, sh["v0"] + 1.9, text_sprite("12 WALLS PER CASTLE", HEAVY, 84, WHITE, tracking=6), W / 2, 120)
        title_in(img, t, sh["v0"] + 1.8, sh["v1"], text_sprite("TWO HITS TO BREAK", HEAVY, 84, WHITE, tracking=6), W / 2, 120)
        for v, e in events_in(sh, {"stone"}):
            if e["hp"] == 0:
                title_in(img, t, v, min(v + 1.3, sh["v1"]), text_sprite("BREACH!", HEAVY_I, 150, FIRE1, stroke=4, stroke_fill=(140, 30, 10), glow=(255, 110, 20)),
                         W / 2, H - 170)
    elif sid == "flank":
        specs_frame(img, t, smooth(u / 0.4) * (1 - smooth((u - 3.6) / 0.4)))
        title_in(img, t, sh["v0"] + 0.2, sh["v0"] + 1.4, text_sprite("PINCH.", HEAVY, 96, WHITE, tracking=8), W / 2, 130)
        title_in(img, t, sh["v0"] + 1.3, sh["v0"] + 2.5, text_sprite("SLIDE.", HEAVY, 96, WHITE, tracking=8), W / 2, 130)
        title_in(img, t, sh["v0"] + 2.4, sh["v1"], text_sprite("DEFEND ALL THREE SIDES.", HEAVY, 80, WHITE, tracking=6), W / 2, 130)
    elif sid == "solo":
        lower_third(img, t, sh["v0"] + 0.1, sh["v1"] + 0.3, "PLAY THE CPU", "solo  ·  starts instantly", TEAL)
    elif sid == "friend":
        lower_third(img, t, sh["v0"] - 0.1, sh["v1"], "OR FACE A FRIEND", "same table  ·  two pairs of Specs", AMBER)
    elif sid == "sudden":
        el = meta.get("elapsed", 75)
        m_, s_ = divmod(el, 60)
        timer = text_sprite(f"{int(m_)}:{s_:04.1f}", HEAVY, 54, (255, 90, 70), glow=(255, 40, 20))
        place(img, timer, W / 2, 64, 1.0, smooth(u / 0.3))
        title_in(img, t, sh["v0"] + 0.25, sh["v0"] + 2.2, text_sprite("SUDDEN DEATH", HEAVY_I, 130, (255, 80, 60), stroke=3, stroke_fill=(60, 0, 0), glow=(255, 30, 10)),
                 W / 2, H / 2 - 20)
        title_in(img, t, sh["v0"] + 2.1, sh["v1"], text_sprite("THE WALLS COME DOWN", HEAVY, 84, WHITE, tracking=6), W / 2, H - 140)
    elif sid == "crown":
        if t >= IMPACT_V + 0.45:
            title_in(img, t, IMPACT_V + 0.45, sh["v1"], text_sprite("CROWN DESTROYED", HEAVY_I, 110, WHITE, tracking=4, glow=(255, 120, 30)), W / 2, 130)
            title_in(img, t, IMPACT_V + 1.0, sh["v1"], text_sprite("AMBER TAKES THE MATCH", HEAVY, 60, AMBER, tracking=6), W / 2, 215)
        # letterbox squeeze during the slow-mo
        lb = int(70 * smooth((t - 35.1) / 0.3) * (1 - smooth((t - 36.9) / 0.4)))
        if lb > 0:
            ImageDraw.Draw(img).rectangle((0, 0, W, lb), fill=BLACK)
            ImageDraw.Draw(img).rectangle((0, H - lb, W, H), fill=BLACK)
    elif sid == "specs":
        feature_card(img, t, sh["v0"] + 0.1, sh["v1"] + 0.2)
    # hard cut helpers: tiny flash on every cut
    flash(img, 0.18 * math.exp(-u * 20), WHITE)
    return img


def frame(t):
    if t < BOX1:
        img = cold_open(t)
    elif t >= CTA0:
        img = cta(t)
    else:
        sh = shot_at(t)
        img = shot_frame(sh, t)
        if sh["id"] == "reveal" and t < BOX1 + 0.45:
            u = smooth((t - BOX1) / 0.45)
            fw = fire_wipe(1.0, t)
            fw.putalpha(fw.getchannel("A").point(lambda v: int(v * (1 - u))))
            img.alpha_composite(fw)
    return img.convert("RGB")


if PREVIEW:
    for x in PREVIEW.split(","):
        frame(float(x)).save(os.path.join(BUILD, f"preview_{float(x):05.2f}.png"))
    sys.exit(0)

# ---------------------------------------------------------------- audio cue sheet
CUES = []


def cue(t, path, v=1.0):
    if 0 <= t < DUR and os.path.exists(path):
        CUES.append((t, path, v))


L = lambda n: os.path.join(LENS_SFX, n + ".wav")
S = lambda n: os.path.join(SFX, n + ".wav")
cue(0.0, S("Rumble"), 0.5)
cue(2.2, S("Riser"), 0.45)
cue(3.0, S("Slam"), 1.0)
cue(3.0, L("CastleStone"), 0.8)
cue(5.3, S("Whoosh"), 0.9)
cue(6.05, S("Chime"), 0.45)                                    # AR spawn
for sh in SHOTS:
    for v, e in events_in(sh, {"shield"}):
        cue(v, L("CastleShield"), 0.75)
    for v, e in events_in(sh, {"stone"}):
        cue(v, L("CastleStone"), 0.9 if e["hp"] == 0 else 0.65)
        if e["hp"] == 0:
            cue(v, S("Rumble"), 0.6)
    for v, e in events_in(sh, {"sudden"}):
        cue(v, S("Rumble"), 0.55)
    for v, e in events_in(sh, {"win"}):
        cue(v, L("CastleWin"), 1.0)
        cue(v, S("Boom"), 0.9)
        cue(v + 0.05, S("Sparkle"), 0.6)
    for v, e in events_in(sh, {"serve"}):
        cue(v, S("Whoosh"), 0.8)
    if sh["id"] == "serve":
        seen = set()
        for k in range(round((sh["v1"] - sh["v0"]) * FPS)):
            m = FMETA.get(f"serve_{k:04d}", {})
            if m.get("phase") == "c":
                n = math.ceil(m["clock"] - 1e-6)
                if n not in seen:
                    seen.add(n)
                    cue(sh["v0"] + k / FPS, S("Blip"), 0.8)
    if sh["id"] == "rally":
        for v, e in events_in(sh, {"shield"})[:4]:
            cue(v, S("Swish"), 0.4)
cue(IMPACT_V - 1.9, S("Riser"), 0.55)
for i in range(5):
    cue(SHOT["specs"]["v0"] + 0.65 + i * 0.32, S("Blip"), 0.35)
cue(CTA0, S("Slam"), 0.9)

inputs = ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", S("Score")]
AF = "aformat=sample_rates=48000:channel_layouts=stereo"
filt = [f"[1:a]{AF},atrim=0:{DUR},volume=0.62,afade=t=out:st={DUR - 1.2}:d=1.2[m]"]
labels = ["[m]"]
for i, (ct, f, v) in enumerate(CUES):
    inputs += ["-i", f]
    ms = int(ct * 1000)
    filt.append(f"[{i + 2}:a]{AF},volume={v},adelay={ms}|{ms}[s{i}]")
    labels.append(f"[s{i}]")
filt.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.8:attack=1:release=60,volume=0.88,atrim=0:{DUR}[a]")

cmd = ["ffmpeg", "-y", "-loglevel", "error"] + inputs + [
    "-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[a]",
    "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high",
    "-g", "60", "-bf", "2", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", OUT]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for n in range(NF):
    p.stdin.write(frame(n / FPS).tobytes())
    if n % 150 == 0:
        print(f"[promo] {n}/{NF}", flush=True)
p.stdin.close()
sys.exit(p.wait())
