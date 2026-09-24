"""Castle Clash promo: gameplay timeline + edit decision list.

  python3 sim.py            run both match segments, pick shot windows, write build/timeline.json + build/edl.json

The simulation is a line-for-line port of Assets/Scripts/CastleClashSimulation.ts (same rules, rail, walls,
swept collisions, speed-up and sudden death), so everything the promo shows is what the Lens actually does.
Only the shield *inputs* are directed: a predictor steers each shield toward the incoming fireball and the
director decides whether that defender blocks (with a chosen rebound offset) or misses.

Lens board coordinates, cm: x across the table (-20..20), z along it (-30..30). Teal (side 0) owns +z, Amber -z.
"""
import json, math, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
os.makedirs(BUILD, exist_ok=True)

RULES = dict(speed=28, maxSpeed=62, shieldSpeed=40, shieldWidth=7, suddenDeath=75, countdown=3, wins=2)
DT = 1 / 240
SAMPLE = 2                      # keep every 2nd step -> 120 Hz timeline
SUDDEN_ORDER = [3, 4, 2, 5, 1, 6, 0, 7, 8, 10, 9, 11]


def clamp(x, a, b):
    return max(a, min(b, x))


def rail(s, side):
    k = 1 if side == 0 else -1
    s = clamp(s, 0, 54)
    if s < 13:
        return -14, k * (27 - s), True
    if s > 41:
        return 14, k * (14 + s - 41), True
    return s - 27, k * 14, False


def walls():
    out = []
    for side in range(2):
        k = 1 if side == 0 else -1
        for i in range(8):
            out.append(dict(x=-10.5 + i * 3, z=k * 18, hx=1.48, hz=0.8, side=side, index=side * 12 + i, kind="wall"))
        for f in range(2):
            for j in range(2):
                out.append(dict(x=-12 if f == 0 else 12, z=k * (21 + j * 5), hx=0.8, hz=2.48, side=side,
                                index=side * 12 + 8 + f * 2 + j, kind="wall"))
    return out


WALLS = walls()
RAILS = [dict(x=-20, z=0, hx=0.5, hz=31, side=-1, index=-1, kind="rail"), dict(x=20, z=0, hx=0.5, hz=31, side=-1, index=-1, kind="rail"),
         dict(x=0, z=-30, hx=20, hz=0.5, side=-1, index=-1, kind="rail"), dict(x=0, z=30, hx=20, hz=0.5, side=-1, index=-1, kind="rail")]


class Sim:
    """Port of CastleClashSimulation (phases practice/countdown/playing/round/match)."""

    def __init__(self, seed=1):
        self.rnd = random.Random(seed)
        self.s = dict(phase="practice", clock=0.0, elapsed=0.0, x=0.0, z=0.0, vx=0.0, vz=0.0, shields=[27.0, 27.0],
                      targets=[27.0, 27.0], walls=[2] * 24, scores=[0, 0], winner=-1)
        self.sudden = 0
        self.events = []
        self.t = 0.0
        self.ghost = False

    def clone(self):
        c = Sim.__new__(Sim)
        c.rnd, c.sudden, c.events, c.t, c.ghost = self.rnd, self.sudden, [], self.t, True
        c.s = {k: (list(v) if isinstance(v, list) else v) for k, v in self.s.items()}
        return c

    def cue(self, kind, **kw):
        if not self.ghost:
            self.events.append(dict(t=round(self.t, 5), kind=kind, x=round(self.s["x"], 3), z=round(self.s["z"], 3), **kw))

    def ready(self):
        self.s["phase"], self.s["clock"] = "countdown", RULES["countdown"]

    def serve(self, angle=None):
        s = self.s
        a = angle if angle is not None else self.rnd.random() * 0.9 - 0.45
        d = -1 if sum(s["scores"]) % 2 == 0 else 1
        s["x"] = s["z"] = 0.0
        s["vx"], s["vz"] = math.sin(a) * RULES["speed"], d * math.cos(a) * RULES["speed"]
        s["phase"] = "playing"
        self.cue("serve")

    def step(self, dt, shields=True):
        s = self.s
        self.t += dt
        if s["phase"] == "match":
            return
        for i in range(2):
            s["shields"][i] += clamp(s["targets"][i] - s["shields"][i], -RULES["shieldSpeed"] * dt, RULES["shieldSpeed"] * dt)
        if s["phase"] == "countdown":
            s["clock"] -= dt
            if s["clock"] <= 0:
                self.serve(getattr(self, "serve_angle", None))
            return
        if s["phase"] == "round":
            s["clock"] -= dt
            return
        if s["phase"] != "playing":
            return
        s["elapsed"] += dt
        wanted = min(12, max(0, math.floor((s["elapsed"] - RULES["suddenDeath"]) / 2) + 1))
        while self.sudden < wanted:
            w = SUDDEN_ORDER[self.sudden]
            s["walls"][w] = s["walls"][12 + w] = 0
            self.cue("sudden", index=w)
            self.sudden += 1
        self.move(dt, shields)
        if abs(s["x"]) > 18.8:
            s["x"] = clamp(s["x"], -18.8, 18.8)
            s["vx"] = -math.copysign(1, s["x"]) * abs(s["vx"])
        if abs(s["z"]) > 28.8:
            s["z"] = clamp(s["z"], -28.8, 28.8)
            s["vz"] = -math.copysign(1, s["z"]) * abs(s["vz"])

    def move(self, dt, shields):
        s = self.s
        remaining = dt
        for _ in range(8):
            if remaining <= 1e-6:
                break
            shapes = list(RAILS) + [w for w in WALLS if s["walls"][w["index"]] > 0]
            for side in (0, 1):
                shapes.append(dict(x=0, z=28.3 if side == 0 else -28.3, hx=12.8, hz=0.8, side=side, index=-1, kind="rear"))
            for side in range(2):
                px, pz, fl = rail(s["shields"][side], side)
                if shields:
                    w2 = RULES["shieldWidth"] / 2
                    shapes.append(dict(x=px, z=pz, hx=0.55 if fl else w2, hz=w2 if fl else 0.55, side=side, index=-1, kind="shield", flank=fl))
                shapes.append(dict(x=0, z=26 if side == 0 else -26, hx=2.7, hz=2, side=side, index=-1, kind="crown"))
            first, hit, nx, nz = remaining + 1, None, 0, 0
            for r in shapes:
                c = self.sweep(r, remaining)
                if c and c[0] < first:
                    first, hit, nx, nz = c[0], r, c[1], c[2]
            if not hit:
                s["x"] += s["vx"] * remaining
                s["z"] += s["vz"] * remaining
                break
            s["x"] += s["vx"] * first
            s["z"] += s["vz"] * first
            remaining -= first
            if hit["kind"] == "crown":
                s["winner"] = 1 - hit["side"]
                s["scores"][s["winner"]] += 1
                s["phase"] = "match" if s["scores"][s["winner"]] >= RULES["wins"] else "round"
                s["clock"] = 2.5
                s["vx"] = s["vz"] = 0.0
                self.cue("win", side=hit["side"])
                return
            speed = math.hypot(s["vx"], s["vz"])
            if hit["kind"] == "shield":
                if nx:
                    s["x"] = hit["x"] + nx * (hit["hx"] + 0.702)
                else:
                    s["z"] = hit["z"] + nz * (hit["hz"] + 0.702)
                px, pz, fl = rail(s["shields"][hit["side"]], hit["side"])
                off = clamp(((s["z"] - pz) if fl else (s["x"] - px)) / (RULES["shieldWidth"] / 2), -1, 1)
                speed = min(RULES["maxSpeed"], speed * 1.05)
                if not fl:
                    a = off * 0.95
                    s["vx"] = math.sin(a) * speed
                    s["vz"] = (-1 if hit["side"] == 0 else 1) * math.cos(a) * speed
                else:
                    s["vx"] = (-1 if px < 0 else 1) * speed * 0.75
                    s["vz"] = (-1 if hit["side"] == 0 else 1) * speed * math.sqrt(1 - 0.75 * 0.75)
                self.cue("shield", side=hit["side"], flank=fl, offset=round(off, 3), speed=round(speed, 2))
            else:
                if nx:
                    s["vx"] = -s["vx"]
                if nz:
                    s["vz"] = -s["vz"]
                if hit["kind"] == "wall":
                    s["walls"][hit["index"]] -= 1
                    f = max(RULES["speed"], speed * 0.92) / speed
                    s["vx"] *= f
                    s["vz"] *= f
                    self.cue("stone", index=hit["index"], side=hit["side"], hp=s["walls"][hit["index"]])
                else:
                    self.cue("bounce", what=hit["kind"])
            mag = math.hypot(s["vx"], s["vz"])
            s["x"] += s["vx"] / mag * 0.002
            s["z"] += s["vz"] / mag * 0.002

    def sweep(self, r, mx):
        s = self.s
        rad = 0.7
        if r["kind"] == "shield" and abs(s["x"] - r["x"]) < r["hx"] + rad and abs(s["z"] - r["z"]) < r["hz"] + rad:
            dx = (r["hx"] + rad) - abs(s["x"] - r["x"])
            dz = (r["hz"] + rad) - abs(s["z"] - r["z"])
            nx = (1 if s["x"] >= r["x"] else -1) if dx < dz else 0
            nz = (1 if s["z"] >= r["z"] else -1) if dx >= dz else 0
            if s["vx"] * nx + s["vz"] * nz < 0:
                return (0.0, nx, nz)
        enter, exit_, nx, nz = -math.inf, math.inf, 0, 0
        for axis in ("x", "z"):
            p, v, c = s[axis], s["v" + axis], r[axis]
            h = r["h" + axis] + rad
            if abs(v) < 1e-9:
                if p < c - h or p > c + h:
                    return None
                continue
            a, b = (c - h - p) / v, (c + h - p) / v
            n = -1 if v > 0 else 1
            if a > b:
                a, b = b, a
            if a > enter:
                enter = a
                nx, nz = (n, 0) if axis == "x" else (0, n)
            exit_ = min(exit_, b)
        if enter > exit_ or exit_ < 0 or enter < -0.00001 or enter > mx:
            return None
        return (max(0.0, enter), nx, nz)


# ---------------------------------------------------------------- director
def rail_param(x, z, side):
    """Nearest rail parameter (0..54) to a board point: front span s in [13, 41], flanks s < 13 (x=-14) / s > 41 (x=+14)."""
    zz = z * (1 if side == 0 else -1)
    cands = [(clamp(x + 27, 13, 41), None), (clamp(27 - zz, 0, 13), None), (clamp(zz - 14 + 41, 41, 54), None)]
    best, bd = 27.0, 1e9
    for p, _ in cands:
        qx, qz, _f = rail(p, side)
        d = (qx - x) ** 2 + (qz - z) ** 2
        if d < bd:
            bd, best = d, p
    return best


def pins(events, gap=0.02, limit=5):
    """Episodes where the fireball is pinned against the back of a shield (a Lens bug: the shield rebound always
    heads for the centre, which from behind is back into the shield). Returns [(t_start, t_end)]."""
    out, run, start, last = [], 0, 0.0, -1.0
    for e in events:
        if e["kind"] != "shield":
            continue
        if e["t"] - last < gap:
            run += 1
        else:
            if run > limit:
                out.append((start, last))
            run, start = 1, e["t"]
        last = e["t"]
    if run > limit:
        out.append((start, last))
    return out


def dedup(evs, gap=0.02):
    out, last = [], -1.0
    for e in evs:
        if e["t"] - last >= gap:
            out.append(e)
        last = e["t"]
    return out


def stuck(events, longest=0.4):
    return any(b - a > longest for a, b in pins(events))


def predict(sim, side, horizon=2.5):
    """Where the fireball will first reach this side's shield rail (walls, rails included; shields ghosted)."""
    g = sim.clone()
    k = 1 if side == 0 else -1
    t = 0.0
    while t < horizon and g.s["phase"] == "playing":
        x, z = g.s["x"], g.s["z"]
        zz = z * k
        front = zz >= 14 - 1.25 and abs(x) <= 14.6 and zz < 20
        flank = abs(x) >= 14 - 1.25 and abs(x) < 15.3 and 13 < zz < 28
        if (front or flank) and g.s["vz"] * k > -1e-6 or (flank and zz > 13):
            return rail_param(x, z, side), t, (x, z)
        g.step(DT * 2, shields=False)
        t += DT * 2
    return None


class Director:
    """Per-side intent: block with a chosen rebound offset, or let one through."""

    def __init__(self, rnd, miss=(0.15, 0.15), aggression=0.75, lag=(0.0, 0.0)):
        self.rnd, self.miss, self.aggr, self.lag = rnd, list(miss), aggression, lag
        self.plan = [None, None]        # (event count at plan time, will_block, offset)
        self.last_dir = [0, 0]
        self.hold = [False, False]
        self.cache = [(None, None), (None, None)]

    def update(self, sim):
        s = sim.s
        if s["phase"] != "playing":
            for side in range(2):
                s["targets"][side] = 27.0 + 6 * math.sin(sim.t * (1.1 + side * 0.4) + side)
            return
        n = len(sim.events)
        for side in range(2):
            k = 1 if side == 0 else -1
            coming = s["vz"] * k > 0 or abs(s["z"]) > 13 and s["z"] * k > 0
            if not coming:
                # drift back toward the middle of the front span, a touch of life
                s["targets"][side] = 27.0 + 3 * math.sin(sim.t * 1.7 + side * 2)
                self.plan[side] = None
                continue
            if self.plan[side] is None or self.plan[side][0] != n:
                block = self.rnd.random() >= self.miss[side]
                off = self.rnd.uniform(-self.aggr, self.aggr)
                self.plan[side] = (n, block, off)
            if self.hold[side]:
                continue
            zz, x = s["z"] * k, s["x"]
            if zz > 14.8 and abs(x) < 13.3:
                # fireball got behind the shield line: get the shield out of its way (the Lens pins a ball that
                # meets the back of a shield), parking on the far flank until it comes back out
                s["targets"][side] = 54.0 if x < 0 else 0.0
                continue
            _, block, off = self.plan[side]
            key = (n, int(sim.t * 20))                 # re-predict at 20 Hz or on any new contact
            if self.cache[side][0] != key:
                self.cache[side] = (key, predict(sim, side))
            pr = self.cache[side][1]
            if pr is None:
                continue
            p, tt, (px, pz) = pr
            if block:
                s["targets"][side] = clamp(p - off * RULES["shieldWidth"] / 2, 0, 54)
            else:
                # a believable miss: commit to the wrong side of the ball
                s["targets"][side] = clamp(p + (1 if off >= 0 else -1) * RULES["shieldWidth"] * 0.95, 0, 54)


def run(seed, seconds, miss, setup=None, stop_on_win=True, practice=0.0, serve_angle=None, hooks=None):
    sim = Sim(seed)
    if serve_angle is not None:
        sim.serve_angle = serve_angle
    if setup:
        setup(sim)
    d = Director(random.Random(seed * 7 + 1), miss)
    samples = []
    steps = int(seconds / DT)
    readied = practice <= 0
    if readied and sim.s["phase"] == "practice":
        sim.ready()
    for n in range(steps):
        if not readied and sim.t >= practice:
            sim.ready()
            readied = True
        if hooks:
            hooks(sim, d)
        d.update(sim)
        sim.step(DT)
        if n % SAMPLE == 0:
            s = sim.s
            samples.append([round(sim.t, 5), round(s["x"], 3), round(s["z"], 3), round(s["shields"][0], 3), round(s["shields"][1], 3),
                            s["phase"][0], round(s["elapsed"], 3), round(s["clock"], 3)])
        if stop_on_win and sim.s["phase"] in ("round", "match") and sim.t > sim.events[-1]["t"] + 3.0:
            break
        if n % 240 == 0 and stuck(sim.events[-40:]):
            break
    return sim, samples


# ---------------------------------------------------------------- segment A: reveal, serve, rallies, damage
def segment_a():
    for seed in range(1, 400):
        sim, samples = run(seed, 58.0, miss=(0.22, 0.26), practice=3.5, serve_angle=0.28)
        ev = sim.events
        print(f"[sim] A seed {seed}: t={sim.t:.1f} win={any(e['kind'] == 'win' for e in ev)} stuck={stuck(ev)}", flush=True)
        if any(e["kind"] == "win" for e in ev) or stuck(ev):
            continue
        shield = dedup([e for e in ev if e["kind"] == "shield"])
        destroyed = [e for e in ev if e["kind"] == "stone" and e["hp"] == 0]
        cracked = [e for e in ev if e["kind"] == "stone" and e["hp"] == 1]
        flank = [e for e in shield if e["flank"]]
        if len(shield) >= 16 and len(destroyed) >= 3 and len(cracked) >= 5 and len(flank) >= 2:
            print(f"[sim] segment A seed={seed}: {len(shield)} blocks, {len(cracked)} cracks, {len(destroyed)} walls down, "
                  f"{len(flank)} flank blocks", flush=True)
            return seed, sim, samples
    raise SystemExit("no satisfying segment A seed")


# ---------------------------------------------------------------- segment B: sudden death -> crown
def segment_b(walls_from):
    def setup(sim):
        s = sim.s
        s["walls"] = list(walls_from)
        s["scores"] = [1, 1]                  # deciding round: whoever breaks a crown takes the match
        s["phase"] = "playing"
        s["elapsed"] = RULES["suddenDeath"] - 1.2
        s["x"], s["z"] = 3.0, -4.0
        s["vx"], s["vz"] = 18.0, 40.0
        s["shields"], s["targets"] = [30.0, 22.0], [30.0, 22.0]

    for seed in range(1, 600):
        def hooks(sim, d, _st={}):
            # amber stays sharp; teal starts slipping once the front of its castle is gone
            front_gone = sum(1 for i in range(8) if sim.s["walls"][i] == 0)
            d.miss = [0.12 if front_gone < 4 else 0.55, 0.06]
        sim, samples = run(seed, 26.0, miss=(0.12, 0.06), setup=setup, hooks=hooks)
        ev = sim.events
        print(f"[sim] B seed {seed}: t={sim.t:.1f} win={[e['side'] for e in ev if e['kind'] == 'win']} stuck={stuck(ev)}", flush=True)
        win = [e for e in ev if e["kind"] == "win"]
        if not win or win[0]["side"] != 0 or stuck(ev):
            continue
        tw = win[0]["t"]
        sudden = [e for e in ev if e["kind"] == "sudden"]
        before = [e for e in ev if e["kind"] == "shield" and tw - 4.0 < e["t"] < tw]
        if 7.0 < tw < 20.0 and len(sudden) >= 4 and len(before) >= 2:
            print(f"[sim] segment B seed={seed}: teal crown falls at t={tw:.2f}s after {len(sudden)} sudden-death drops", flush=True)
            return seed, sim, samples
    raise SystemExit("no satisfying segment B seed")


# ---------------------------------------------------------------- edit decision list
def best_window(events, length, t_lo, t_hi, score):
    best = None
    t = t_lo
    bad = pins(events)
    while t + length <= t_hi:
        sc = score([e for e in events if t <= e["t"] < t + length], t)
        if any(a < t + length + 0.1 and b > t - 0.1 for a, b in bad):
            sc -= 1000
        if best is None or sc > best[0]:
            best = (sc, t)
        t += 0.05
    return round(best[1], 3)


def main():
    seed_a, A, sa = segment_a()
    walls_mid = [2] * 24
    for e in A.events:
        if e["kind"] == "stone":
            walls_mid[e["index"]] = e["hp"]
    seed_b, B, sb = segment_b(A.s["walls"])
    evA, evB = A.events, B.events
    serve_t = next(e["t"] for e in evA if e["kind"] == "serve")
    tw = next(e["t"] for e in evB if e["kind"] == "win")

    def n(evs, kind, **kw):
        return len(dedup([e for e in evs if e["kind"] == kind and all(e.get(k) == v for k, v in kw.items())]))

    # Cuts sit on the score's bar lines (120 BPM, 2 s bars): 6 reveal, 10 serve, 14 rally, 18 walls, 22 flank,
    # 26 solo, 28 friend, 30 sudden death, 34 crown (impact on the downbeat at 36), 38 Specs, 42 call to action.
    rally = best_window(evA, 4.0, serve_t + 3, 50, lambda w, t: n(w, "shield") * 2 + sum(e.get("speed", 0) for e in w if e["kind"] == "shield") / 40
                        - 3 * n(w, "stone"))
    walls = best_window(evA, 4.0, serve_t + 3, 55, lambda w, t: 6 * n(w, "stone", hp=0) + 2 * n(w, "stone", hp=1)
                        + (4 if any(e["kind"] == "stone" and e["hp"] == 0 and t + 1.2 < e["t"] < t + 3.0 for e in w) else 0)
                        - (0 if abs(t - rally) > 4.2 else 50))
    flank = best_window(evA, 4.0, serve_t + 3, 55, lambda w, t: 5 * sum(1 for e in w if e["kind"] == "shield" and e["flank"] and e["side"] == 0)
                        + n(w, "shield", side=0) - (0 if abs(t - rally) > 4.2 and abs(t - walls) > 4.2 else 50))
    used = [rally, walls, flank]
    far = lambda t, L: all(abs(t - u) > L + 0.2 for u in used)
    solo = best_window(evA, 2.0, serve_t + 3, 55, lambda w, t: n(w, "shield") + n(w, "stone") - (0 if far(t, 4.0) else 50))
    used.append(solo)
    friend = best_window(evA, 2.0, serve_t + 3, 55, lambda w, t: n(w, "shield") + n(w, "stone") - (0 if far(t, 4.0) else 50))
    used.append(friend)
    orbit = best_window(evA, 4.0, serve_t + 3, 55, lambda w, t: n(w, "shield") + 0.5 * n(w, "stone") - (0 if far(t, 4.0) else 50))
    first_sudden = next(e["t"] for e in evB if e["kind"] == "sudden")

    def lin(v0, v1, s0, speed=1.0):
        return [(v0, s0), (v1, s0 + (v1 - v0) * speed)]

    shots = [
        dict(id="reveal", seg="A", cam="reveal", v0=6.0, v1=10.0, map=lin(6.0, 10.0, 0.0)),
        dict(id="serve", seg="A", cam="serve", v0=10.0, v1=14.0, map=lin(10.0, 14.0, serve_t - 2.6)),
        dict(id="rally", seg="A", cam="rally", v0=14.0, v1=18.0, map=lin(14.0, 18.0, rally)),
        dict(id="walls", seg="A", cam="walls", v0=18.0, v1=22.0, map=lin(18.0, 22.0, walls)),
        dict(id="flank", seg="A", cam="flank", v0=22.0, v1=26.0, map=lin(22.0, 26.0, flank)),
        dict(id="solo", seg="A", cam="solo", v0=26.0, v1=28.0, map=lin(26.0, 28.0, solo)),
        dict(id="friend", seg="A", cam="friend", v0=28.0, v1=30.0, map=lin(28.0, 30.0, friend)),
        dict(id="sudden", seg="B", cam="sudden", v0=30.0, v1=34.0, map=lin(30.0, 34.0, first_sudden - 0.5)),
        # crown: real time into the final approach, ramp to ~0.25x through the impact on the 36.0 downbeat, recover
        dict(id="crown", seg="B", cam="crown", v0=34.0, v1=38.0,
             map=[(34.0, tw - 1.55), (35.3, tw - 0.25), (36.0, tw), (36.9, tw + 0.25), (38.0, tw + 1.45)]),
        dict(id="specs", seg="A", cam="specs", v0=38.0, v1=42.0, map=lin(38.0, 42.0, orbit)),
    ]
    edl = dict(shots=shots, serve_t=serve_t, crown_t=tw, seeds=dict(A=seed_a, B=seed_b),
               box=dict(v0=0.0, v1=6.0), cta=dict(v0=42.0, v1=45.0), duration=45.0)
    json.dump(dict(A=dict(samples=sa, events=evA, walls_start=[2] * 24),
                   B=dict(samples=sb, events=evB, walls_start=list(A.s["walls"]))), open(os.path.join(BUILD, "timeline.json"), "w"))
    json.dump(edl, open(os.path.join(BUILD, "edl.json"), "w"), indent=1)
    for s in shots:
        seg = evA if s["seg"] == "A" else evB
        lo, hi = s["map"][0][1], s["map"][-1][1]
        w = [e for e in seg if lo <= e["t"] < hi]
        print(f"[edl] {s['id']:7s} v{s['v0']:5.1f}-{s['v1']:5.1f}  sim {lo:6.2f}-{hi:6.2f}  "
              f"shield={n(w, 'shield')} stone={n(w, 'stone')} down={n(w, 'stone', hp=0)} sudden={n(w, 'sudden')} win={n(w, 'win')}")


if __name__ == "__main__":
    main()
