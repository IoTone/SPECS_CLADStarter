"""Laser Duck promo: 320x180 pixel canvas -> 1280x720 nearest upscale, piped to ffmpeg."""
import math, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "renders")
SFX = "/Users/dkords/dev/projects/iotone/SPECS_CladStarter/Assets/GeneratedSFX"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "LaserDuck_Promo_720p.mp4")
PREVIEW = os.environ.get("PREVIEW")  # comma list of seconds -> dump PNGs instead of video

W, H, S, FPS = 320, 180, 4, 30
DUR = 31.0
NF = int(DUR * FPS)

BG = (12, 8, 34)
YEL = (255, 222, 40)
RED = (255, 40, 40)
GRN = (40, 200, 110)
WHT = (240, 240, 255)
BLK = (0, 0, 0)

def font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)

F_BIG = font("/System/Library/Fonts/Supplemental/Arial Black.ttf", 30)
F_MED = font("/System/Library/Fonts/Supplemental/Arial Black.ttf", 16)
F_SM = font("/System/Library/Fonts/Menlo.ttc", 10, 1)
F_XS = font("/System/Library/Fonts/Menlo.ttc", 8, 1)

def sprite(name, h):
    im = Image.open(os.path.join(R, name)).convert("RGBA")
    im = im.crop(im.getbbox())
    w = max(1, round(im.width * h / im.height))
    im = im.resize((w, h), Image.LANCZOS)
    a = im.getchannel("A").point(lambda v: 255 if v > 110 else 0)
    im.putalpha(a)
    return im

DUCK_FRONT = sprite("RubberDuck_180_4.png", 96)
DUCK_BIG = sprite("RubberDuck_180_4.png", 250)
DUCK_34 = sprite("RubberDuck_215_15.png", 100)
SHIELD = sprite("OShield_0_4.png", 70)
SHIELD_34 = sprite("OShield_25_12.png", 90)
TURN = [sprite(f"RubberDuck_turn_{i:03d}.png", 84) for i in range(48)]

random.seed(7)
STARS = [(random.uniform(0, W), random.uniform(0, H), random.choice((0.3, 0.6, 1.2))) for _ in range(90)]

def clamp01(x):
    return max(0.0, min(1.0, x))

def ease(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3

def stars(d, t, speed=40, tint=None):
    for x, y, z in STARS:
        xx = (x - t * speed * z) % W
        c = tint or ((200, 200, 255) if z > 1 else (110, 110, 170) if z > 0.5 else (70, 70, 120))
        d.point((int(xx), int(y)), fill=c)
        if z > 1 and speed > 80:
            d.line((int(xx), int(y), int(xx) + 3, int(y)), fill=c)

def text(d, xy, s, f, fill=WHT, anchor="mm", stroke=1, sfill=BLK):
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=sfill)

def paste(img, spr, cx, cy):
    img.alpha_composite(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)))

def laser(d, x0, y0, x1, y1, th=2):
    d.line((x0, y0, x1, y1), fill=RED, width=th + 2)
    d.line((x0, y0, x1, y1), fill=(255, 200, 200), width=max(1, th - 1))

def blink(t, rate=2.0):
    return (t * rate) % 1.0 < 0.6

# ---- audio cue list (seconds, file, volume) ----
CUES = []
def cue(t, f, v=1.0):
    CUES.append((t, f, v))

# scene timings
cue(0.9, "DuckSqueak.wav", 1.0)
cue(1.9, "DuckSqueak.wav", 1.0)
cue(3.4, "LaserShot.wav", 1.0)
cue(3.55, "LaserShot.wav", 1.0)
for i in range(6):
    cue(9.3 + i * 0.75, "LaserShot.wav", 0.9)
for i in range(5):
    cue(14.8 + i * 0.8, "LaserShot.wav", 0.8)
    cue(14.8 + i * 0.8 + 0.35, "ShieldDeflect.wav", 0.7)
cue(22.0, "PlayerHit.wav", 1.0)
cue(26.2, "DuckSqueak.wav", 1.0)
cue(29.2, "LaserShot.wav", 1.0)

def frame(t):
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    shake = (0, 0)

    if t < 3.0:  # S1: innocent ducky
        stars(d, t, 10)
        bob = math.sin(t * 5) * 3
        paste(img, DUCK_FRONT, W / 2, 100 + bob)
        if t > 0.4:
            text(d, (W / 2, 24), "AWW. A RUBBER DUCKY.", F_SM, WHT)
        if t > 1.4:
            text(d, (W / 2, 38), "SO INNOCENT.", F_SM, (180, 180, 220))
        if 0.9 < t < 1.2 or 1.9 < t < 2.2:
            text(d, (W / 2 + 52, 68), "squeak!", F_XS, YEL)
    elif t < 5.5:  # S2: WRONG.
        k = ease((t - 3.0) / 0.35)
        img.paste((40, 0, 10, 255), (0, 0, W, H))
        d = ImageDraw.Draw(img); d.fontmode = "1"
        stars(d, t, 10, (120, 30, 40))
        big = DUCK_BIG if k >= 1 else DUCK_FRONT.resize((int(DUCK_FRONT.width * (1 + 1.6 * k)), int(DUCK_FRONT.height * (1 + 1.6 * k))), Image.NEAREST)
        paste(img, big, W / 2, 120 + 40 * k)
        if t > 3.4:
            # eye beams straight at the viewer
            for ex in (-22, 22):
                laser(d, W / 2 + ex, 72, W / 2 + ex * 4, H + 20, 3)
            if t < 3.5:
                img.paste((255, 255, 255, 255), (0, 0, W, H))
                d = ImageDraw.Draw(img); d.fontmode = "1"
            shake = (random.randint(-3, 3), random.randint(-2, 2)) if t < 4.0 else (0, 0)
            text(d, (W / 2, 30), "WRONG.", F_BIG, RED, stroke=2, sfill=WHT if blink(t, 3) else BLK)
    elif t < 9.0:  # S3: title
        tt = t - 5.5
        stars(d, t, 90)
        paste(img, TURN[int(tt * 14) % 48], W / 2, 118)
        drop = 60 * (1 - ease(tt / 0.5))
        text(d, (W / 2 + 2, 34 - drop + 2), "LASER DUCK", F_BIG, RED, stroke=0)
        text(d, (W / 2, 34 - drop), "LASER DUCK", F_BIG, YEL, stroke=2)
        if tt > 0.8:
            text(d, (W / 2, 58), "- A LENS FOR SPECS -", F_SM, WHT)
        if tt > 1.8 and blink(t):
            text(d, (W / 2, 168), "IT HAS LASER EYES. WE CHECKED.", F_XS, (255, 150, 150))
    elif t < 14.0:  # S4: get too close
        tt = t - 9.0
        stars(d, t, 25)
        paste(img, DUCK_34, 90, 112)
        ex, ey = 110, 78
        for i in range(6):
            lt = tt - 0.3 - i * 0.75
            if 0 <= lt < 0.6:
                p = lt / 0.6
                x = ex + (W + 30 - ex) * p
                y = ey + (H * 0.4 - ey) * p
                laser(d, x - 18 * (0.5 + p), y, x, y, 1 + int(p * 4))
        text(d, (W / 2, 20), "GET TOO CLOSE...", F_MED, YEL, stroke=2)
        if tt > 1.6:
            text(d, (232, 120), "...AND IT GETS", F_SM, WHT)
            text(d, (232, 134), "PERSONAL.", F_SM, RED)
        if tt > 3.2:
            text(d, (W / 2, 168), "(it tracks your head. yes, yours.)", F_XS, (170, 170, 210))
    elif t < 20.0:  # S5: shield
        tt = t - 14.0
        stars(d, t, 25)
        paste(img, DUCK_34.resize((70, 70 * DUCK_34.height // DUCK_34.width), Image.NEAREST), 48, 110)
        sx = 250 + (1 - ease(tt / 0.6)) * 120
        sy = 104 + math.sin(t * 3) * 3
        # lasers hit the shield and bounce
        for i in range(5):
            lt = tt - 0.8 - i * 0.8
            if 0 <= lt < 0.35:
                p = lt / 0.35
                x0, y0 = 62, 90
                x = x0 + (sx - 30 - x0) * p
                y = y0 + (sy - y0) * p
                laser(d, x - 16, y, x, y, 2)
            elif 0.35 <= lt < 0.8:
                p = (lt - 0.35) / 0.45
                x = sx - 30 + 30 * p
                y = sy - 150 * p
                laser(d, x, y, x + 6, y - 16, 2)
                if p < 0.35:  # spark
                    for a in range(8):
                        r = 6 + 18 * p
                        d.point((sx - 34 + r * math.cos(a * 0.785), sy + r * math.sin(a * 0.785)), fill=YEL)
                if p < 0.12:
                    text(d, (sx, sy - 48), "DENIED", F_SM, GRN)
        paste(img, SHIELD_34, sx, sy)
        text(d, (W / 2, 18), "YOUR ONLY HOPE:", F_SM, WHT)
        text(d, (W / 2, 34), "THE 'O' SHIELD", F_MED, GRN, stroke=2, sfill=YEL)
        if tt > 1.2:
            text(d, (W / 2 + 10, 168), "strapped to your actual hand. pinky swear.", F_XS, (170, 210, 170))
    elif t < 25.0:  # S6: score + death
        tt = t - 20.0
        stars(d, t, 20)
        text(d, (W / 2, 22), "SCORE = HOW LONG", F_MED, YEL, stroke=2)
        text(d, (W / 2, 42), "YOU SURVIVE", F_MED, YEL, stroke=2)
        secs = min(tt, 2.0) / 2.0 * 7.2
        box = (90, 62, 230, 104)
        d.rectangle(box, fill=(20, 20, 40), outline=WHT)
        text(d, (160, 83), f"TIME {secs:4.1f}s", F_MED, WHT if tt < 2.0 else RED, stroke=1)
        if tt >= 2.0:
            if tt < 2.25:
                img.paste((200, 0, 0, 255), (0, 0, W, H))
                d = ImageDraw.Draw(img); d.fontmode = "1"
            if tt < 2.8:
                shake = (random.randint(-5, 5), random.randint(-4, 4))
            text(d, (W / 2, 124), "SHOT DOWN!", F_MED, RED, stroke=2, sfill=WHT)
        if tt > 2.9:
            text(d, (W / 2, 148), "OUR DEV'S BEST: 7.2 SECONDS.", F_SM, WHT)
            text(d, (W / 2, 162), "BEAT THAT. (PLEASE. IT'S EMBARRASSING.)", F_XS, (255, 170, 170))
    elif t < 27.5:  # S7: disclaimer gag
        tt = t - 25.0
        stars(d, t, 10)
        bob = math.sin(t * 6) * 2
        paste(img, TURN[0], W / 2, 106 + bob)
        text(d, (W / 2, 26), "NO DUCKS WERE HARMED", F_SM, WHT)
        text(d, (W / 2, 40), "IN THE MAKING OF THIS LENS.", F_SM, WHT)
        if tt > 1.1:
            text(d, (W / 2, 164), "several humans were.", F_SM, RED)
        if 1.2 < tt < 1.6:
            text(d, (W / 2 + 46, 74), "squeak.", F_XS, YEL)
    else:  # S8: CTA
        tt = t - 27.5
        stars(d, t, 60)
        paste(img, TURN[int(tt * 14) % 48].resize((64, 64 * TURN[0].height // TURN[0].width), Image.NEAREST), 46, 96)
        paste(img, SHIELD, 276, 96)
        text(d, (W / 2 + 2, 42), "LASER DUCK", F_BIG, RED, stroke=0)
        text(d, (W / 2, 40), "LASER DUCK", F_BIG, YEL, stroke=2)
        text(d, (W / 2, 72), "BUILT FOR SPECS", F_SM, WHT)
        text(d, (W / 2, 96), "LENS FEST", F_MED, GRN, stroke=2, sfill=BLK)
        text(d, (W / 2, 114), "SEPTEMBER", F_SM, YEL)
        if blink(t, 1.5):
            text(d, (W / 2, 146), "PINCH TO START", F_SM, WHT)
        text(d, (W / 2, 168), "QUACK RESPONSIBLY.", F_XS, (170, 170, 210))
        if tt > 3.1:  # fade out
            a = int(255 * clamp01((tt - 3.1) / 0.4))
            img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, a)))

    if shake != (0, 0):
        base = Image.new("RGBA", (W, H), BLK + (255,))
        base.paste(img, shake)
        img = base
    return img.convert("RGB")

# CRT scanlines at output resolution
SCAN = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
sd = ImageDraw.Draw(SCAN)
for y in range(0, H * S, S):
    sd.line((0, y + S - 1, W * S, y + S - 1), fill=(0, 0, 0, 70))

def final(t):
    big = frame(t).resize((W * S, H * S), Image.NEAREST).convert("RGBA")
    big.alpha_composite(SCAN)
    return big.convert("RGB")

if PREVIEW:
    for s in PREVIEW.split(","):
        final(float(s)).save(os.path.join(HERE, f"preview_{s}.png"))
    sys.exit(0)

# ---- audio: music bed + SFX cues ----
inputs = ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W*S}x{H*S}", "-r", str(FPS), "-i", "-",
          "-i", os.path.join(SFX, "BackgroundMusic.wav")]
filt = [f"[1:a]atrim=0:{DUR},volume=0.55,afade=t=out:st={DUR-2}:d=2[m]"]
labels = ["[m]"]
for i, (ct, f, v) in enumerate(CUES):
    inputs += ["-i", os.path.join(SFX, f)]
    ms = int(ct * 1000)
    filt.append(f"[{i+2}:a]volume={v},adelay={ms}|{ms}[s{i}]")
    labels.append(f"[s{i}]")
filt.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.95,atrim=0:{DUR}[a]")

cmd = ["ffmpeg", "-y", "-loglevel", "error"] + inputs + [
    "-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[a]",
    "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-tune", "animation",
    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", OUT]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for n in range(NF):
    p.stdin.write(final(n / FPS).tobytes())
p.stdin.close()
sys.exit(p.wait())
