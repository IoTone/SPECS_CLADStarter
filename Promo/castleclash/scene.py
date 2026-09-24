"""Castle Clash promo: Blender scene + per-frame state from the gameplay timeline.

  Blender -b -P scene.py -- still SHOT[,SHOT] [K]   look-dev: render frame K (default middle) of each shot to build/still_<shot>.png
  Blender -b -P scene.py -- render [SHOT,SHOT]      render every frame of the shots in build/edl.json to build/frames/

Everything is authored in Lens board centimetres (x across, y up, z along; Teal owns +z) under a root empty scaled
0.01, so the world is true scale in metres: depth of field, light falloff and rubble motion read as a real
miniature on a real table. Lens (x, y, z) maps to Blender local (x, -z, y), so Teal sits nearest the default camera.
The game state for every frame comes from build/timeline.json (a port of the Lens simulation, see sim.py).
"""
import bpy, bmesh, math, os, sys, json, random
from mathutils import Vector, Euler, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
FRAMES = os.path.join(BUILD, "frames")
os.makedirs(FRAMES, exist_ok=True)
FPS = 30
U = 0.01
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["still"]
MODE = ARGS[0]

TL = json.load(open(os.path.join(BUILD, "timeline.json")))
EDL = json.load(open(os.path.join(BUILD, "edl.json")))
RATE = 120.0

STONE = (0.80, 0.77, 0.66)
TEAL = (0.10, 0.95, 0.88)
AMBER = (1.0, 0.62, 0.12)
TEAM = [TEAL, AMBER]
BOARD_TOP = 0.16


def lin(c):
    return tuple(v ** 2.2 for v in c[:3])


def P(x, y, z):
    """Lens board cm -> Blender local cm."""
    return Vector((x, -z, y))


def W(v):
    """Blender local cm -> world metres."""
    return Vector(v) * U


def clamp(x, a, b):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x, 0, 1)
    return x * x * (3 - 2 * x)


def back_out(x, k=1.7):
    x = clamp(x, 0, 1) - 1
    return 1 + (k + 1) * x ** 3 + k * x ** 2


# ---------------------------------------------------------------- the sim geometry (same as sim.py / the Lens)
def rail(s, side):
    k = 1 if side == 0 else -1
    s = clamp(s, 0, 54)
    if s < 13:
        return -14, k * (27 - s), True
    if s > 41:
        return 14, k * (14 + s - 41), True
    return s - 27, k * 14, False


def lens_walls():
    out = []
    for side in range(2):
        k = 1 if side == 0 else -1
        for i in range(8):
            out.append(dict(x=-10.5 + i * 3, z=k * 18, hx=1.48, hz=0.8, side=side, index=side * 12 + i))
        for f in range(2):
            for j in range(2):
                out.append(dict(x=-12 if f == 0 else 12, z=k * (21 + j * 5), hx=0.8, hz=2.48, side=side, index=side * 12 + 8 + f * 2 + j))
    return out


# ---------------------------------------------------------------- materials
def node_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    return m, m.node_tree.nodes, m.node_tree.links


def bsdf_of(nodes):
    return nodes.get("Principled BSDF")


def set_in(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def wrap_fx(m, base_socket, holo_color=(0.35, 0.95, 1.0), holo_strength=6.0):
    """Object colour drives FX: R = crack, G = hologram (AR spawn), B = visibility (0 fades out)."""
    nodes, links = m.node_tree.nodes, m.node_tree.links
    out = nodes.get("Material Output")
    info = nodes.new("ShaderNodeObjectInfo")
    sep = nodes.new("ShaderNodeSeparateColor")
    links.new(info.outputs["Color"], sep.inputs[0])
    # hologram: fresnel-edged cyan emission with a scanline
    fres = nodes.new("ShaderNodeFresnel")
    fres.inputs["IOR"].default_value = 1.25
    tex = nodes.new("ShaderNodeTexCoord")
    sepz = nodes.new("ShaderNodeSeparateXYZ")
    links.new(tex.outputs["Object"], sepz.inputs[0])
    wave = nodes.new("ShaderNodeTexWave")
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 0.8
    links.new(tex.outputs["Object"], wave.inputs["Vector"])
    hmix = nodes.new("ShaderNodeMath")
    hmix.operation = "ADD"
    links.new(fres.outputs[0], hmix.inputs[0])
    wmul = nodes.new("ShaderNodeMath")
    wmul.operation = "MULTIPLY"
    wmul.inputs[1].default_value = 0.35
    links.new(wave.outputs["Fac"], wmul.inputs[0])
    links.new(wmul.outputs[0], hmix.inputs[1])
    em = nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = lin(holo_color) + (1,)
    hs = nodes.new("ShaderNodeMath")
    hs.operation = "MULTIPLY"
    hs.inputs[1].default_value = holo_strength
    links.new(hmix.outputs[0], hs.inputs[0])
    links.new(hs.outputs[0], em.inputs["Strength"])
    tr = nodes.new("ShaderNodeBsdfTransparent")
    add = nodes.new("ShaderNodeAddShader")
    links.new(em.outputs[0], add.inputs[0])
    links.new(tr.outputs[0], add.inputs[1])
    mix_h = nodes.new("ShaderNodeMixShader")
    links.new(sep.outputs["Green"], mix_h.inputs[0])
    links.new(base_socket, mix_h.inputs[1])
    links.new(add.outputs[0], mix_h.inputs[2])
    tr2 = nodes.new("ShaderNodeBsdfTransparent")
    mix_v = nodes.new("ShaderNodeMixShader")
    links.new(sep.outputs["Blue"], mix_v.inputs[0])
    links.new(tr2.outputs[0], mix_v.inputs[1])
    links.new(mix_h.outputs[0], mix_v.inputs[2])
    links.new(mix_v.outputs[0], out.inputs["Surface"])
    try:
        m.surface_render_method = "DITHERED"
    except Exception:
        pass
    return sep


def stone_mat(name, color=STONE, scale=2.2, crackable=True):
    m, nodes, links = node_mat(name)
    b = bsdf_of(nodes)
    tex = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 8
    links.new(tex.outputs["Object"], noise.inputs["Vector"])
    info = nodes.new("ShaderNodeObjectInfo")
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = lin(tuple(c * 0.72 for c in color)) + (1,)
    ramp.color_ramp.elements[1].color = lin(color) + (1,)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    # per-brick tint
    tint = nodes.new("ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.blend_type = "MULTIPLY"
    links.new(ramp.outputs["Color"], tint.inputs[6])
    rr = nodes.new("ShaderNodeValToRGB")
    rr.color_ramp.elements[0].color = (0.82, 0.8, 0.76, 1)
    rr.color_ramp.elements[1].color = (1.0, 0.98, 0.94, 1)
    links.new(info.outputs["Random"], rr.inputs["Fac"])
    links.new(rr.outputs["Color"], tint.inputs[7])
    tint.inputs[0].default_value = 1.0
    # crack lines (voronoi edges) that glow like embers when the object's crack amount (R) is up
    vor = nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 1.6
    links.new(tex.outputs["Object"], vor.inputs["Vector"])
    crk = nodes.new("ShaderNodeMapRange")
    crk.inputs["From Min"].default_value = 0.0
    crk.inputs["From Max"].default_value = 0.05
    crk.inputs["To Min"].default_value = 1.0
    crk.inputs["To Max"].default_value = 0.0
    links.new(vor.outputs["Distance"], crk.inputs["Value"])
    sep = nodes.new("ShaderNodeSeparateColor")
    links.new(info.outputs["Color"], sep.inputs[0])
    amt = nodes.new("ShaderNodeMath")
    amt.operation = "MULTIPLY"
    links.new(crk.outputs["Result"], amt.inputs[0])
    links.new(sep.outputs["Red"], amt.inputs[1])
    dark = nodes.new("ShaderNodeMix")
    dark.data_type = "RGBA"
    links.new(amt.outputs[0], dark.inputs[0])
    links.new(tint.outputs[2], dark.inputs[6])
    dark.inputs[7].default_value = (0.05, 0.03, 0.02, 1)
    links.new(dark.outputs[2], b.inputs["Base Color"])
    set_in(b, "Emission Color", lin((1.0, 0.35, 0.05)) + (1,))
    es = nodes.new("ShaderNodeMath")
    es.operation = "MULTIPLY"
    es.inputs[1].default_value = 7.0 if crackable else 0.0
    links.new(amt.outputs[0], es.inputs[0])
    links.new(es.outputs[0], b.inputs["Emission Strength"])
    b.inputs["Roughness"].default_value = 0.82
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.02
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], b.inputs["Normal"])
    wrap_fx(m, b.outputs[0])
    return m


def world_coords(nodes, links, per_cm=1.0):
    """Board-space coordinates in cm (world metres x 100), so textures stay put on static scaled boxes."""
    geo = nodes.new("ShaderNodeNewGeometry")
    mp = nodes.new("ShaderNodeVectorMath")
    mp.operation = "SCALE"
    mp.inputs["Scale"].default_value = 100.0 * per_cm
    links.new(geo.outputs["Position"], mp.inputs[0])
    return mp.outputs[0]


def brick_texture_mat(name, color=STONE, scale=1.2):
    """Masonry for the big pieces (rear walls, towers, pedestals); scale = bricks per cm-ish."""
    m, nodes, links = node_mat(name)
    b = bsdf_of(nodes)
    wc0 = world_coords(nodes, links)
    sp = nodes.new("ShaderNodeSeparateXYZ")
    links.new(wc0, sp.inputs[0])
    hz = nodes.new("ShaderNodeMath")
    hz.operation = "ADD"
    links.new(sp.outputs["X"], hz.inputs[0])
    links.new(sp.outputs["Y"], hz.inputs[1])
    cmb = nodes.new("ShaderNodeCombineXYZ")
    links.new(hz.outputs[0], cmb.inputs["X"])
    links.new(sp.outputs["Z"], cmb.inputs["Y"])
    wc = cmb.outputs[0]
    br = nodes.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = scale
    br.inputs["Mortar Size"].default_value = 0.025
    br.inputs["Color1"].default_value = lin(color) + (1,)
    br.inputs["Color2"].default_value = lin(tuple(c * 0.82 for c in color)) + (1,)
    br.inputs["Mortar"].default_value = lin((0.35, 0.33, 0.3)) + (1,)
    br.offset_frequency, br.squash_frequency = 2, 2
    mp = nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1, 1, 1.25)
    links.new(wc, mp.inputs["Vector"])
    links.new(mp.outputs[0], br.inputs["Vector"])
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.8
    noise.inputs["Detail"].default_value = 6
    links.new(wc, noise.inputs["Vector"])
    mul = nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "OVERLAY"
    mul.inputs[0].default_value = 0.35
    links.new(br.outputs["Color"], mul.inputs[6])
    links.new(noise.outputs["Color"], mul.inputs[7])
    links.new(mul.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.5
    bump.inputs["Distance"].default_value = 0.03
    links.new(br.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], b.inputs["Normal"])
    wrap_fx(m, b.outputs[0])
    return m


def metal_mat(name, color, rough=0.28, emit=None, emit_strength=0.0):
    m, nodes, links = node_mat(name)
    b = bsdf_of(nodes)
    b.inputs["Base Color"].default_value = lin(color) + (1,)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = rough
    if emit:
        set_in(b, "Emission Color", lin(emit) + (1,))
        set_in(b, "Emission Strength", emit_strength)
    wrap_fx(m, b.outputs[0])
    return m


def plain_mat(name, color, rough=0.5, emit=None, emit_strength=0.0, coat=0.0, metallic=0.0, fx=True):
    m, nodes, links = node_mat(name)
    b = bsdf_of(nodes)
    b.inputs["Base Color"].default_value = lin(color) + (1,)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    set_in(b, "Coat Weight", coat)
    if emit:
        set_in(b, "Emission Color", lin(emit) + (1,))
        set_in(b, "Emission Strength", emit_strength)
    if fx:
        wrap_fx(m, b.outputs[0])
    return m


def glow_mat(name, color, strength, alpha_fresnel=False):
    """Pure emission; object colour R = flash boost, B = visibility."""
    m, nodes, links = node_mat(name)
    nodes.remove(bsdf_of(nodes))
    out = nodes.get("Material Output")
    info = nodes.new("ShaderNodeObjectInfo")
    sep = nodes.new("ShaderNodeSeparateColor")
    links.new(info.outputs["Color"], sep.inputs[0])
    em = nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = lin(color) + (1,)
    boost = nodes.new("ShaderNodeMath")
    boost.operation = "MULTIPLY_ADD"
    boost.inputs[1].default_value = strength * 4
    boost.inputs[2].default_value = strength
    links.new(sep.outputs["Red"], boost.inputs[0])
    links.new(boost.outputs[0], em.inputs["Strength"])
    tr = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    fac = sep.outputs["Blue"]
    if alpha_fresnel:
        lw = nodes.new("ShaderNodeLayerWeight")
        lw.inputs["Blend"].default_value = 0.45
        pw = nodes.new("ShaderNodeMath")
        pw.operation = "MULTIPLY"
        links.new(lw.outputs["Facing"], pw.inputs[0])
        links.new(sep.outputs["Blue"], pw.inputs[1])
        fac = pw.outputs[0]
    links.new(fac, mix.inputs[0])
    links.new(tr.outputs[0], mix.inputs[1])
    links.new(em.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])
    try:
        m.surface_render_method = "DITHERED"
    except Exception:
        pass
    return m


def shield_mat(name, color):
    """Energy pane: hex cells + fresnel rim, team colour; object colour R = impact flash, B = visibility."""
    m, nodes, links = node_mat(name)
    nodes.remove(bsdf_of(nodes))
    out = nodes.get("Material Output")
    tex = nodes.new("ShaderNodeTexCoord")
    vor = nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 7.0
    links.new(tex.outputs["UV"], vor.inputs["Vector"])
    edge = nodes.new("ShaderNodeMapRange")
    edge.inputs["From Min"].default_value = 0.0
    edge.inputs["From Max"].default_value = 0.08
    edge.inputs["To Min"].default_value = 1.0
    edge.inputs["To Max"].default_value = 0.12
    links.new(vor.outputs["Distance"], edge.inputs["Value"])
    # soft vertical falloff: bright at the emitter, fading upward
    sep_uv = nodes.new("ShaderNodeSeparateXYZ")
    links.new(tex.outputs["UV"], sep_uv.inputs[0])
    fall = nodes.new("ShaderNodeMapRange")
    fall.inputs["From Min"].default_value = 0.0
    fall.inputs["From Max"].default_value = 1.0
    fall.inputs["To Min"].default_value = 1.0
    fall.inputs["To Max"].default_value = 0.25
    links.new(sep_uv.outputs["Y"], fall.inputs["Value"])
    # horizontal edges brighten
    ex = nodes.new("ShaderNodeMath")
    ex.operation = "SUBTRACT"
    ex.inputs[1].default_value = 0.5
    links.new(sep_uv.outputs["X"], ex.inputs[0])
    ea = nodes.new("ShaderNodeMath")
    ea.operation = "ABSOLUTE"
    links.new(ex.outputs[0], ea.inputs[0])
    er = nodes.new("ShaderNodeMapRange")
    er.inputs["From Min"].default_value = 0.40
    er.inputs["From Max"].default_value = 0.5
    er.inputs["To Min"].default_value = 0.0
    er.inputs["To Max"].default_value = 1.2
    links.new(ea.outputs[0], er.inputs["Value"])
    a1 = nodes.new("ShaderNodeMath")
    a1.operation = "MULTIPLY"
    links.new(edge.outputs["Result"], a1.inputs[0])
    links.new(fall.outputs["Result"], a1.inputs[1])
    a2 = nodes.new("ShaderNodeMath")
    a2.operation = "ADD"
    links.new(a1.outputs[0], a2.inputs[0])
    links.new(er.outputs["Result"], a2.inputs[1])
    info = nodes.new("ShaderNodeObjectInfo")
    sep = nodes.new("ShaderNodeSeparateColor")
    links.new(info.outputs["Color"], sep.inputs[0])
    fl = nodes.new("ShaderNodeMath")
    fl.operation = "MULTIPLY_ADD"
    fl.inputs[1].default_value = 3.0
    fl.inputs[2].default_value = 1.0
    links.new(sep.outputs["Red"], fl.inputs[0])
    st = nodes.new("ShaderNodeMath")
    st.operation = "MULTIPLY"
    links.new(a2.outputs[0], st.inputs[0])
    links.new(fl.outputs[0], st.inputs[1])
    em = nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = lin(color) + (1,)
    s2 = nodes.new("ShaderNodeMath")
    s2.operation = "MULTIPLY"
    s2.inputs[1].default_value = 9.0
    links.new(st.outputs[0], s2.inputs[0])
    links.new(s2.outputs[0], em.inputs["Strength"])
    alpha = nodes.new("ShaderNodeMath")
    alpha.operation = "MULTIPLY"
    alpha.use_clamp = True
    links.new(st.outputs[0], alpha.inputs[0])
    links.new(sep.outputs["Blue"], alpha.inputs[1])
    a3 = nodes.new("ShaderNodeMath")
    a3.operation = "MULTIPLY_ADD"
    a3.use_clamp = True
    a3.inputs[1].default_value = 0.8
    a3.inputs[2].default_value = 0.0
    links.new(alpha.outputs[0], a3.inputs[0])
    tr = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(a3.outputs[0], mix.inputs[0])
    links.new(tr.outputs[0], mix.inputs[1])
    links.new(em.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    return m


def fire_mat(name, core=False):
    """Fireball: white-hot core, turbulent orange shell (4D noise W animated per frame)."""
    m, nodes, links = node_mat(name)
    nodes.remove(bsdf_of(nodes))
    out = nodes.get("Material Output")
    em = nodes.new("ShaderNodeEmission")
    if core:
        em.inputs["Color"].default_value = lin((1.0, 0.92, 0.62)) + (1,)
        em.inputs["Strength"].default_value = 60.0
        links.new(em.outputs[0], out.inputs["Surface"])
        return m, None
    tex = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.inputs["Scale"].default_value = 2.2
    noise.inputs["Detail"].default_value = 6
    noise.inputs["Roughness"].default_value = 0.6
    links.new(tex.outputs["Object"], noise.inputs["Vector"])
    ramp = nodes.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.35, (0.8, 0.08, 0.0, 1)
    e[1].position, e[1].color = 0.75, (1.0, 0.75, 0.2, 1)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], em.inputs["Color"])
    lw = nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    inv = nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    links.new(lw.outputs["Facing"], inv.inputs[1])
    dens = nodes.new("ShaderNodeMath")
    dens.operation = "MULTIPLY"
    dens.use_clamp = True
    links.new(inv.outputs[0], dens.inputs[0])
    links.new(noise.outputs["Fac"], dens.inputs[1])
    d2 = nodes.new("ShaderNodeMath")
    d2.operation = "MULTIPLY"
    d2.use_clamp = True
    d2.inputs[1].default_value = 2.4
    links.new(dens.outputs[0], d2.inputs[0])
    es = nodes.new("ShaderNodeMath")
    es.operation = "MULTIPLY"
    es.inputs[1].default_value = 30.0
    links.new(d2.outputs[0], es.inputs[0])
    links.new(es.outputs[0], em.inputs["Strength"])
    tr = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(d2.outputs[0], mix.inputs[0])
    links.new(tr.outputs[0], mix.inputs[1])
    links.new(em.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    return m, noise


def wood_mat():
    m, nodes, links = node_mat("TableWood")
    b = bsdf_of(nodes)
    tex = nodes.new("ShaderNodeTexCoord")
    mp = nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.35, 3.0, 1.0)
    links.new(tex.outputs["Object"], mp.inputs["Vector"])
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.03
    noise.inputs["Detail"].default_value = 4
    links.new(mp.outputs[0], noise.inputs["Vector"])
    wave = nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.inputs["Scale"].default_value = 0.035
    wave.inputs["Distortion"].default_value = 3.5
    wave.inputs["Detail"].default_value = 6
    links.new(mp.outputs[0], wave.inputs["Vector"])
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = lin((0.22, 0.11, 0.05)) + (1,)
    ramp.color_ramp.elements[1].color = lin((0.33, 0.18, 0.09)) + (1,)
    links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.38
    set_in(b, "Coat Weight", 0.35)
    set_in(b, "Coat Roughness", 0.12)
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    links.new(wave.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def tile_mat():
    m, nodes, links = node_mat("FieldTiles")
    b = bsdf_of(nodes)
    wc = world_coords(nodes, links)
    br = nodes.new("ShaderNodeTexBrick")
    br.inputs["Scale"].default_value = 0.2
    br.inputs["Mortar Size"].default_value = 0.012
    br.inputs["Brick Width"].default_value = 1.0
    br.inputs["Row Height"].default_value = 1.0
    br.offset = 0.0
    br.inputs["Color1"].default_value = lin((0.34, 0.40, 0.38)) + (1,)
    br.inputs["Color2"].default_value = lin((0.28, 0.34, 0.33)) + (1,)
    br.inputs["Mortar"].default_value = lin((0.10, 0.12, 0.12)) + (1,)
    links.new(wc, br.inputs["Vector"])
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.35
    noise.inputs["Detail"].default_value = 8
    links.new(wc, noise.inputs["Vector"])
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "OVERLAY"
    mix.inputs[0].default_value = 0.4
    links.new(br.outputs["Color"], mix.inputs[6])
    links.new(noise.outputs["Color"], mix.inputs[7])
    links.new(mix.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.62
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    bump.inputs["Distance"].default_value = 0.02
    links.new(br.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], b.inputs["Normal"])
    wrap_fx(m, b.outputs[0])
    return m


# ---------------------------------------------------------------- mesh helpers
ROOT = None
COLL = None


def link(o, parent=True):
    COLL.objects.link(o)
    if parent:
        o.parent = ROOT
    o.color = (0, 0, 1, 1)
    return o


def mesh_obj(name, bm, mat, parent=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    me.materials.append(mat)
    return link(bpy.data.objects.new(name, me), parent)


_box_cache = {}


def box_mesh(bevel=0.08, seg=2):
    key = (bevel, seg)
    if key in _box_cache:
        return _box_cache[key]
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=bevel, segments=seg, affect="EDGES", profile=0.6)
    me = bpy.data.meshes.new(f"box_{bevel}")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    _box_cache[key] = me
    return me


def box(name, center, size, mat, bevel=0.08, parent=True):
    """center/size in Blender local cm."""
    me = box_mesh(bevel)
    o = bpy.data.objects.new(name, me)
    o.data = me
    o.location = center
    o.scale = size
    link(o, parent)
    if len(o.material_slots) == 0:
        o.data.materials.append(mat) if not o.data.materials else None
    o.material_slots[0].link = "OBJECT"
    o.material_slots[0].material = mat
    return o


def cyl(name, center, r, h, mat, verts=32, r2=None, parent=True, cap=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=verts, radius1=r, radius2=r if r2 is None else r2, depth=h)
    o = mesh_obj(name, bm, mat, parent)
    for p in o.data.polygons:
        p.use_smooth = True
    o.location = center
    return o


def sphere(name, r, mat, seg=24, ring=12, parent=True):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=r)
    o = mesh_obj(name, bm, mat, parent)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def prism(name, pts2d, depth, mat, parent=True):
    """Extrude a 2D outline (x, y in the XZ plane of the object) by depth along local Y."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, -depth / 2, y)) for x, y in pts2d]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]:
        v.co.y += depth
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_obj(name, bm, mat, parent)


def diamond_pts(r):
    return [(0, r), (r * 0.72, 0), (0, -r), (-r * 0.72, 0)]


def sun_pts(r, rays=12):
    pts = []
    for i in range(rays * 2):
        a = math.pi * i / rays
        rr = r if i % 2 == 0 else r * 0.62
        pts.append((rr * math.sin(a), rr * math.cos(a)))
    return pts


# ---------------------------------------------------------------- scene build
class Castle:
    pass


def build():
    global ROOT, COLL
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    COLL = sc.collection
    ROOT = bpy.data.objects.new("BoardRoot", None)
    COLL.objects.link(ROOT)
    ROOT.scale = (U, U, U)
    R = {}

    M = dict(
        stone=stone_mat("Stone"),
        big=brick_texture_mat("Masonry", STONE, 0.42),
        tower=brick_texture_mat("TowerMasonry", (0.86, 0.83, 0.72), 0.5),
        slate=plain_mat("Slate", (0.26, 0.31, 0.34), 0.55, coat=0.2),
        tile=tile_mat(),
        copper=metal_mat("Copper", (0.95, 0.56, 0.30), 0.3),
        gold=metal_mat("Gold", (1.0, 0.78, 0.36), 0.18),
        wood=wood_mat(),
        pole=metal_mat("Pole", (0.3, 0.3, 0.32), 0.4),
    )
    for i, c in enumerate(TEAM):
        M[f"team{i}"] = plain_mat(f"Team{i}", tuple(v * 0.8 for v in c), 0.55, coat=0.3)
        M[f"cloth{i}"] = plain_mat(f"Cloth{i}", tuple(v * 0.75 for v in c), 0.8)
        M[f"gem{i}"] = plain_mat(f"Gem{i}", c, 0.05, emit=c, emit_strength=6.0, coat=1.0)
        M[f"rail{i}"] = glow_mat(f"Rail{i}", c, 3.0)
        M[f"shield{i}"] = shield_mat(f"Shield{i}", c)
        M[f"roof{i}"] = plain_mat(f"Roof{i}", tuple(v * 0.55 for v in c), 0.45, coat=0.5)
        M[f"crest{i}"] = plain_mat(f"Crest{i}", (1, 0.95, 0.85), 0.2, emit=c, emit_strength=0.8, metallic=0.8)
    M["spark"] = glow_mat("Spark", (1.0, 0.62, 0.18), 18.0)
    M["ember"] = glow_mat("Ember", (1.0, 0.36, 0.06), 12.0)
    M["dust"] = plain_mat("Dust", (0.7, 0.66, 0.58), 1.0)
    M["ring"] = glow_mat("ScanRing", (0.35, 0.95, 1.0), 8.0, alpha_fresnel=False)
    M["core"], _ = fire_mat("FireCore", core=True)
    M["shell"], R["fire_noise"] = fire_mat("FireShell")
    M["trail"] = glow_mat("Trail", (1.0, 0.45, 0.08), 14.0)
    M["marker"] = glow_mat("Marker", (0.8, 0.95, 1.0), 2.0)
    M["panel"] = plain_mat("PanelGlass", (0.03, 0.035, 0.05), 0.55, coat=0.0)
    M["panel_rim"] = glow_mat("PanelRim", (0.6, 0.8, 1.0), 0.9)
    M["track"] = plain_mat("Track", (0.18, 0.2, 0.24), 0.4)
    M["hand"] = glow_mat("Hand", (0.85, 0.93, 1.0), 2.2, alpha_fresnel=False)
    M["winner"] = glow_mat("WinnerCrest", AMBER, 10.0)
    M["ceramic"] = plain_mat("Ceramic", (0.92, 0.9, 0.86), 0.25, coat=0.6, fx=False)
    M["book1"] = plain_mat("Book1", (0.45, 0.12, 0.1), 0.6, fx=False)
    M["book2"] = plain_mat("Book2", (0.12, 0.2, 0.32), 0.6, fx=False)
    M["pages"] = plain_mat("Pages", (0.9, 0.86, 0.76), 0.8, fx=False)
    R["M"] = M

    # table + props (real world: never hologram / never fade)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=160)
    t = mesh_obj("Table", bm, M["wood"])
    t.location = (0, 0, -1.8)
    mug = cyl("Mug", (58, 18, -1.8 + 5.2), 4.2, 10.4, M["ceramic"], 48)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=3.7, radius2=3.7, depth=0.4)
    coffee = mesh_obj("Coffee", bm, plain_mat("Coffee", (0.09, 0.05, 0.03), 0.1, coat=1.0, fx=False))
    coffee.location = (58, 18, -1.8 + 9.6)
    bpy.ops.mesh.primitive_torus_add(major_radius=2.6, minor_radius=0.6, location=(0, 0, 0), rotation=(math.pi / 2, 0, 0))
    h = bpy.context.active_object
    h.name = "MugHandle"
    h.data.materials.append(M["ceramic"])
    h.parent = ROOT
    h.location = (62.6, 18, 3.4)
    h.scale = (0.8, 1, 1)
    h.color = (0, 0, 1, 1)
    for n, (z0, mat, rot) in enumerate(((0, M["book1"], 8), (3.2, M["book2"], -5))):
        b = box(f"Book{n}", (-62, 30, -1.8 + 1.6 + z0), (24, 17, 3.1), mat, 0.3)
        b.rotation_euler = (0, 0, math.radians(rot))
        p = box(f"Pages{n}", (-62.4, 30, -1.8 + 1.6 + z0), (23, 16.4, 2.7), M["pages"], 0.1)
        p.rotation_euler = (0, 0, math.radians(rot))

    board = []
    board.append(box("BoardBase", P(0, -0.9, 0), (42, 62, 1.8), M["slate"], 0.35))
    board.append(box("Field", P(0, 0.08, 0), (38, 58, 0.16), M["tile"], 0.05))
    for x in (-20, 20):
        board.append(box(f"TrimX{x}", P(x, 0.5, 0), (1, 60, 1), M["copper"], 0.2))
    for z in (-30, 30):
        board.append(box(f"TrimZ{z}", P(0, 0.5, z), (40, 1, 1), M["copper"], 0.2))
    # alignment marker at the board centre (the shared colocation check)
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=False, segments=64, radius=2.4)
    bmesh.ops.create_circle(bm, cap_ends=False, segments=64, radius=2.0)
    mk = mesh_obj("Marker", bm, M["marker"])
    mk.data.polygons  # ring built as edges; give it thickness with a skin-less solidify
    bpy.data.objects.remove(mk)
    bpy.ops.mesh.primitive_torus_add(major_radius=2.2, minor_radius=0.08, location=(0, 0, 0))
    mk = bpy.context.active_object
    mk.name = "Marker"
    mk.data.materials.append(M["marker"])
    mk.parent = ROOT
    mk.location = P(0, 0.2, 0)
    mk.color = (0, 0, 1, 1)
    board.append(mk)
    R["board"] = board

    # rails + castles
    castles = []
    for side in range(2):
        k = 1 if side == 0 else -1
        c = Castle()
        c.side = side
        c.parts = []            # (object, spawn delay) for the AR reveal
        # glowing shield track
        for n, (a, b) in enumerate((((-13.5, 14), (13.5, 14)), ((-14, 14), (-14, 27.5)), ((14, 14), (14, 27.5)))):
            (x0, z0), (x1, z1) = a, b
            cx, cz = (x0 + x1) / 2, k * (z0 + z1) / 2
            sx, sz = abs(x1 - x0) + 0.4, abs(z1 - z0) + 0.4
            r = box(f"Rail{side}_{n}", P(cx, 0.25, cz), (sx if sx > 1 else 0.36, sz if sz > 1 else 0.36, 0.14), M[f"rail{side}"], 0.04)
            c.parts.append(r)
        # rear wall + merlons
        rw = box(f"Rear{side}", P(0, 1.8, k * 28.3), (25.6, 1.6, 3.6), M["big"], 0.12)
        c.parts.append(rw)
        for i in range(9):
            c.parts.append(box(f"RearM{side}_{i}", P(-12 + i * 3, 4.0, k * 28.3), (1.4, 1.6, 0.9), M["big"], 0.1))
        # towers
        c.flags = []
        for x in (-10, 10):
            tw = cyl(f"Tower{side}_{x}", P(x, 3.4, k * 26), 2.15, 6.8, M["tower"], 40)
            c.parts.append(tw)
            band = cyl(f"TowerBand{side}_{x}", P(x, 6.9, k * 26), 2.35, 0.5, M["copper"], 40)
            c.parts.append(band)
            for m in range(8):
                a = m / 8 * 2 * math.pi
                mm = box(f"TowerM{side}_{x}_{m}", P(x + 1.95 * math.cos(a), 7.6, k * 26 + 1.95 * math.sin(a)), (0.9, 0.9, 1.0), M["tower"], 0.08)
                mm.rotation_euler = (0, 0, -a)
                c.parts.append(mm)
            roof = cyl(f"Roof{side}_{x}", P(x, 9.6, k * 26), 1.9, 3.4, M[f"roof{side}"], 40, r2=0.05)
            c.parts.append(roof)
            pole = cyl(f"Pole{side}_{x}", P(x, 12.4, k * 26), 0.07, 3.0, M["pole"], 8)
            c.parts.append(pole)
            # flag: 10 x 5 grid, animated per frame
            bm = bmesh.new()
            bmesh.ops.create_grid(bm, x_segments=10, y_segments=5, size=1.0)
            for v in bm.verts:
                v.co = Vector(((v.co.x + 1) * 1.25, 0, v.co.y * 0.7))
            fl = mesh_obj(f"Flag{side}_{x}", bm, M[f"cloth{side}"])
            fl.location = P(x + 0.05, 13.3, k * 26)
            fl.data.materials.append(M[f"cloth{side}"])
            c.flags.append((fl, [v.co.copy() for v in fl.data.vertices], 1 if x > 0 else -1))
            c.parts.append(fl)
        # banners with the kingdom crest on the inner face of the rear wall
        c.banners = []
        for x in (-6.5, 6.5):
            ban = box(f"Banner{side}_{x}", (0, 0, 0), (2.4, 0.12, 3.2), M[f"cloth{side}"], 0.04)
            ban.parent = None
            pivot = bpy.data.objects.new(f"BannerPivot{side}_{x}", None)
            link(pivot)
            pivot.location = P(x, 3.5, k * (28.3 - 0.95))
            if side == 1:
                pivot.rotation_euler = (0, 0, math.pi)
            ban.parent = pivot
            ban.location = (0, 0, -1.6)
            crest = prism(f"CrestB{side}_{x}", diamond_pts(0.8) if side == 0 else sun_pts(0.85), 0.1, M[f"crest{side}"], parent=False)
            crest.parent = pivot
            crest.location = (0, -0.1, -1.55)
            rod = cyl(f"BannerRod{side}_{x}", (0, 0, 0), 0.08, 2.9, M["copper"], 8, parent=False)
            rod.parent = pivot
            rod.rotation_euler = (0, math.pi / 2, 0)
            c.banners.append(pivot)
            c.parts += [ban, crest, rod]
        # crown on its pedestal
        ped = box(f"Pedestal{side}", P(0, 1.5, k * 26), (4.8, 3.3, 3.0), M["big"], 0.15)
        c.parts.append(ped)
        c.parts.append(box(f"PedBand{side}", P(0, 3.25, k * 26), (5.3, 3.7, 0.5), M["copper"], 0.1))
        crown = bpy.data.objects.new(f"Crown{side}", None)
        link(crown)
        crown.location = P(0, 3.5, k * 26)
        ring = cyl(f"CrownRing{side}", (0, 0, 0.55), 1.55, 1.1, M["gold"], 40, cap=False, parent=False)
        ring.parent = crown
        sol = ring.modifiers.new("thick", "SOLIDIFY")
        sol.thickness = 0.18
        crown_parts = [ring]
        for i in range(6):
            a = i / 6 * 2 * math.pi
            sp = cyl(f"CrownSpike{side}_{i}", (1.5 * math.cos(a), 1.5 * math.sin(a), 1.55), 0.32, 1.1, M["gold"], 12, r2=0.02, parent=False)
            sp.parent = crown
            gem = sphere(f"CrownGem{side}_{i}", 0.26, M[f"gem{side}"], 12, 8, parent=False)
            gem.parent = crown
            gem.location = (1.62 * math.cos(a + math.pi / 6), 1.62 * math.sin(a + math.pi / 6), 0.55)
            crown_parts += [sp, gem]
        top = sphere(f"CrownTop{side}", 0.45, M[f"gem{side}"], 16, 10, parent=False)
        top.parent = crown
        top.location = (0, 0, 1.1)
        crown_parts.append(top)
        c.crown, c.crown_parts, c.crown_home = crown, crown_parts, crown.location.copy()
        c.parts += crown_parts
        # shield: copper emitter + energy pane, rotated for the flanks
        sh = bpy.data.objects.new(f"Shield{side}", None)
        link(sh)
        em = box(f"Emitter{side}", (0, 0, 0.35), (7.0, 0.7, 0.5), M["copper"], 0.15, parent=False)
        em.parent = sh
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=12, y_segments=6, size=0.5)
        uv = bm.loops.layers.uv.new()
        for f in bm.faces:
            for lp in f.loops:
                lp[uv].uv = (lp.vert.co.x + 0.5, lp.vert.co.y + 0.5)
        for v in bm.verts:
            x, y = v.co.x, v.co.y
            v.co = Vector((x * 7.0, -0.35 * (1 - (2 * x) ** 2), (y + 0.5) * 3.4 + 0.55))
        pane = mesh_obj(f"Pane{side}", bm, M[f"shield{side}"], parent=False)
        pane.parent = sh
        pane.visible_shadow = False
        c.shield, c.pane, c.emitter = sh, pane, em
        c.parts += [em, pane]
        castles.append(c)
    R["castles"] = castles

    # destructible walls: individual bricks
    rnd = random.Random(4)
    walls = []
    for w in lens_walls():
        long_x = w["hx"] > w["hz"]
        Lw, D = 2 * max(w["hx"], w["hz"]), 2 * min(w["hx"], w["hz"])
        rows, rh = 4, 0.84
        n = max(2, round(Lw / 1.0))
        bricks = []
        for r in range(rows):
            y = BOARD_TOP + rh * (r + 0.5)
            segs = [Lw / n] * n if r % 2 == 0 else [Lw / n / 2] + [Lw / n] * (n - 1) + [Lw / n / 2]
            u = -Lw / 2
            for L in segs:
                cu = u + L / 2
                u += L
                cx, cz = (w["x"] + cu, w["z"]) if long_x else (w["x"], w["z"] + cu)
                sx, sz = (L - 0.06, D - 0.04) if long_x else (D - 0.04, L - 0.06)
                o = box(f"Brick{w['index']}_{len(bricks)}", P(cx, y, cz), (sx, sz, rh - 0.05), M["stone"], 0.07)
                o.rotation_euler = (rnd.uniform(-0.02, 0.02), rnd.uniform(-0.02, 0.02), rnd.uniform(-0.03, 0.03))
                bricks.append(dict(o=o, home=o.location.copy(), rot=o.rotation_euler.copy(), stage=1 if r == rows - 1 else 0, row=r))
        nm = 2 if long_x else 3
        for m_ in range(nm):
            cu = -Lw / 2 + Lw * (m_ + 0.5) / nm
            cx, cz = (w["x"] + cu, w["z"]) if long_x else (w["x"], w["z"] + cu)
            sx, sz = (0.9, D - 0.1) if long_x else (D - 0.1, 0.9)
            o = box(f"Merlon{w['index']}_{m_}", P(cx, BOARD_TOP + rows * rh + 0.35, cz), (sx, sz, 0.7), M["stone"], 0.07)
            bricks.append(dict(o=o, home=o.location.copy(), rot=o.rotation_euler.copy(), stage=1, row=rows))
        walls.append(dict(w=w, bricks=bricks))
    R["walls"] = walls

    # fireball
    fb = bpy.data.objects.new("Fireball", None)
    link(fb)
    core = sphere("FireCore", 0.55, M["core"], 24, 12, parent=False)
    core.parent = fb
    shell = sphere("FireShell", 1.45, M["shell"], 32, 16, parent=False)
    shell.parent = fb
    for o in (core, shell):
        o.visible_shadow = False
    R["fireball"], R["fire_shell"] = fb, shell
    lamp = bpy.data.lights.new("FireLight", "POINT")
    lamp.color = (1.0, 0.55, 0.2)
    lamp.shadow_soft_size = 0.004
    lo = bpy.data.objects.new("FireLight", lamp)
    COLL.objects.link(lo)
    R["fire_light"] = lo
    R["trail"] = []
    for i in range(16):
        o = sphere(f"Trail{i}", 1.0, M["trail"], 12, 8)
        o.visible_shadow = False
        R["trail"].append(o)
    R["sparks"] = []
    for i in range(140):
        o = sphere(f"Spark{i}", 1.0, M["spark"], 8, 4)
        o.visible_shadow = False
        R["sparks"].append(o)
    R["embers"] = []
    for i in range(40):
        o = sphere(f"Ember{i}", 1.0, M["ember"], 8, 4)
        o.visible_shadow = False
        R["embers"].append(o)
    R["dust"] = []
    for i in range(24):
        o = sphere(f"Dust{i}", 1.0, M["dust"], 16, 8)
        o.visible_shadow = False
        R["dust"].append(o)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.012, major_segments=96, location=(0, 0, 0))
    ring = bpy.context.active_object
    ring.name = "ScanRing"
    ring.data.materials.append(M["ring"])
    ring.parent = ROOT
    ring.color = (0, 0, 1, 1)
    ring.visible_shadow = False
    R["scan"] = ring
    impact_lamp = bpy.data.lights.new("ImpactLight", "POINT")
    impact_lamp.color = (1.0, 0.6, 0.25)
    impact_lamp.shadow_soft_size = 0.01
    il = bpy.data.objects.new("ImpactLight", impact_lamp)
    COLL.objects.link(il)
    R["impact_light"] = il
    # winner crest hologram (amber sun) that rises over the arena
    wc = prism("WinnerCrest", sun_pts(4.0, 16), 0.5, M["winner"])
    wc.visible_shadow = False
    R["winner"] = wc

    # the built control: compact panel + slider outside the teal edge, facing the seated player
    panel = bpy.data.objects.new("ControlPanel", None)
    link(panel)
    panel.location = P(0, 3.5, 37.5)
    panel.rotation_euler = (math.radians(-48), 0, 0)
    pl = box("PanelPlate", (0, 0, 0), (26, 0.5, 6.4), M["panel"], 0.9, parent=False)
    pl.parent = panel
    rim = box("PanelRim", (0, 0.3, 0), (26.3, 0.1, 6.6), M["panel_rim"], 0.9, parent=False)
    rim.parent = panel
    rim.visible_shadow = False
    tr = box("SliderTrack", (-2, -0.35, -0.8), (17, 0.2, 0.9), M["track"], 0.4, parent=False)
    tr.parent = panel
    fill = box("SliderFill", (0, -0.4, -0.8), (1, 0.2, 0.9), M["rail0"], 0.4, parent=False)
    fill.parent = panel
    knob = cyl("SliderKnob", (0, -0.6, -0.8), 1.25, 0.6, M["gem0"], 32, parent=False)
    knob.parent = panel
    knob.rotation_euler = (math.pi / 2, 0, 0)
    pause = box("PauseBtn", (9.6, -0.35, -0.8), (4.6, 0.3, 2.6), M["track"], 0.6, parent=False)
    pause.parent = panel
    for n, (txt, x, z, size, mat) in enumerate((("TEAL  0 : 0  AMBER", -2, 1.7, 1.25, M["panel_rim"]), ("Pause", 9.6, -1.25, 0.95, M["panel_rim"]))):
        cu = bpy.data.curves.new(f"PanelText{n}", "FONT")
        cu.body = txt
        cu.size = size
        cu.align_x = "CENTER"
        to = bpy.data.objects.new(f"PanelText{n}", cu)
        COLL.objects.link(to)
        to.parent = panel
        to.location = (x, -0.45, z)
        to.rotation_euler = (math.pi / 2, 0, 0)
        cu.materials.append(mat)
        to.color = (0, 0, 1, 1)
        to.visible_shadow = False
    R["panel"] = dict(root=panel, knob=knob, fill=fill, text=bpy.data.objects["PanelText0"],
                      parts=[pl, rim, tr, fill, knob, bpy.data.objects["PanelText0"]])
    pause.hide_render = True
    bpy.data.objects["PanelText1"].hide_render = True

    # tracked-hand visual (Specs-style joint hand), pinching the knob
    hand = bpy.data.objects.new("Hand", None)
    link(hand)
    hand.parent = panel
    R["hand"] = hand
    R["hand_parts"] = []
    # pinch cursor (what Specs draws where your pinch lands): a ring that tightens onto the knob
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.06, major_segments=64, location=(0, 0, 0), rotation=(math.pi / 2, 0, 0))
    cur = bpy.context.active_object
    cur.name = "PinchCursor"
    cur.data.materials.append(M["hand"])
    cur.parent = panel
    cur.color = (0, 0, 1, 1)
    cur.visible_shadow = False
    R["cursor"] = cur

    # lighting: warm key through a window, cool fill from the room HDRI
    w = bpy.data.worlds.new("Room")
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    bg = nt.nodes.get("Background")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    hdr = None
    for root in ("/Applications/Blender.app/Contents/Resources",):
        for dp, dn, fn in os.walk(root):
            if "interior.exr" in fn and "studiolights" in dp:
                hdr = os.path.join(dp, "interior.exr")
                break
    if hdr:
        env.image = bpy.data.images.load(hdr)
        mp = nt.nodes.new("ShaderNodeMapping")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp.inputs["Rotation"].default_value = (0, 0, math.radians(200))
        nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
        nt.links.new(mp.outputs[0], env.inputs["Vector"])
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.22
    sc.world = w
    key = bpy.data.lights.new("Key", "AREA")
    key.energy, key.size, key.color = 380.0, 0.9, (1.0, 0.80, 0.6)
    ko = bpy.data.objects.new("Key", key)
    COLL.objects.link(ko)
    ko.location = (-1.1, -0.6, 1.5)
    ko.rotation_euler = (Vector((0, 0, 0)) - ko.location).to_track_quat("-Z", "Y").to_euler()
    rim_l = bpy.data.lights.new("Rim", "AREA")
    rim_l.energy, rim_l.size, rim_l.color = 260.0, 0.8, (0.55, 0.75, 1.0)
    ro = bpy.data.objects.new("Rim", rim_l)
    COLL.objects.link(ro)
    ro.location = (1.0, 1.2, 0.9)
    ro.rotation_euler = (Vector((0, 0, 0)) - ro.location).to_track_quat("-Z", "Y").to_euler()
    red = bpy.data.lights.new("Doom", "AREA")
    red.energy, red.size, red.color = 0.0, 0.6, (1.0, 0.1, 0.04)
    do = bpy.data.objects.new("Doom", red)
    COLL.objects.link(do)
    do.location = (0.0, 0.0, 0.7)
    R["key"], R["rim"], R["doom"] = key, rim_l, red

    cd = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cd)
    COLL.objects.link(cam)
    sc.camera = cam
    cd.clip_start, cd.clip_end = 0.01, 60
    cd.dof.use_dof = True
    cd.sensor_width = 36
    R["cam"] = cam
    return sc, R


def build_hand(root, mat):
    """Right hand as joint spheres + bone capsules, in local cm (pinching at the local origin)."""
    parts = []
    # knuckle base points (x across the palm, y toward fingertips); curled pinch pose
    chains = {
        "thumb": [(-2.6, -3.2, -1.2), (-3.3, -1.2, -0.8), (-2.2, 0.6, -0.3), (-0.4, 0.2, 0.0)],
        "index": [(-1.6, 3.0, 0.4), (-1.5, 5.4, 0.2), (-0.9, 5.6, -1.6), (-0.3, 4.3, -2.8), (0.0, 0.0, 0.0)],
        "middle": [(0.3, 3.3, 0.5), (0.6, 6.0, 0.4), (0.9, 6.9, -1.6), (0.9, 6.0, -3.2)],
        "ring": [(2.0, 3.0, 0.4), (2.5, 5.4, 0.2), (2.8, 6.0, -1.4), (2.8, 5.2, -2.8)],
        "pinky": [(3.4, 2.4, 0.2), (4.1, 4.2, 0.0), (4.4, 4.8, -1.2), (4.3, 4.2, -2.3)],
    }
    # fix index tip to the pinch point next to the thumb tip
    chains["index"] = [(-1.6, 3.0, 0.4), (-1.6, 5.3, 0.1), (-1.0, 4.9, -1.5), (-0.3, 0.5, -0.4)]
    chains["index"][-1] = (-0.25, 0.55, 0.05)
    wrist = (0.8, -3.8, 0.0)
    pts = [wrist] + [c[0] for c in chains.values()]
    for pnt in pts:
        s = sphere("HandJ", 0.42, mat, 12, 8, parent=False)
        s.parent = root
        s.location = pnt
        parts.append(s)

    def bone(a, b, r=0.26):
        a, b = Vector(a), Vector(b)
        d = b - a
        o = cyl("HandB", (a + b) / 2, r, d.length, mat, 10, parent=False)
        o.parent = root
        o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        parts.append(o)

    for name, ch in chains.items():
        bone(wrist, ch[0], 0.2)
        for a, b in zip(ch, ch[1:]):
            bone(a, b)
            s = sphere("HandJ", 0.34, mat, 12, 8, parent=False)
            s.parent = root
            s.location = b
            parts.append(s)
    for a, b in zip([c[0] for c in chains.values()], [c[0] for c in chains.values()][1:]):
        bone(a, b, 0.18)
    for o in parts:
        o.visible_shadow = False
        o.color = (0, 0, 1, 1)
    return parts


# ---------------------------------------------------------------- timeline access
class Seg:
    def __init__(self, name):
        d = TL[name]
        self.s = d["samples"]
        self.ev = d["events"]
        self.walls_start = d["walls_start"]
        self.serves = [e["t"] for e in self.ev if e["kind"] == "serve"]
        self.win = next((e for e in self.ev if e["kind"] == "win"), None)
        # wall damage history: index -> [(t, hp_after, x, z)]
        self.dmg = {}
        for e in self.ev:
            if e["kind"] == "stone":
                self.dmg.setdefault(e["index"], []).append((e["t"], e["hp"], e["x"], e["z"]))
            elif e["kind"] == "sudden":
                for idx in (e["index"], 12 + e["index"]):
                    self.dmg.setdefault(idx, []).append((e["t"], 0, None, None))

    def at(self, t):
        i = clamp(t * RATE, 0, len(self.s) - 1.001)
        a = int(i)
        f = i - a
        A, B = self.s[a], self.s[min(a + 1, len(self.s) - 1)]
        return dict(t=t, x=A[1] + (B[1] - A[1]) * f, z=A[2] + (B[2] - A[2]) * f, sh0=A[3] + (B[3] - A[3]) * f,
                    sh1=A[4] + (B[4] - A[4]) * f, phase=A[5], elapsed=A[6], clock=A[7])

    def hp(self, index, t):
        hp = self.walls_start[index]
        for te, h, _, _ in self.dmg.get(index, []):
            if te <= t:
                hp = h
        return hp

    def breaks(self, index):
        """[(t, stage, impact_x, impact_z)] stage 1 = top row falls (2->1), stage 0 = the rest (->0)."""
        out = []
        hp = self.walls_start[index]
        for te, h, x, z in self.dmg.get(index, []):
            if hp == 2 and h <= 1:
                out.append((te, 1, x, z))
            if hp >= 1 and h == 0:
                out.append((te, 0, x, z))
            hp = h
        return out


SEGS = {}


def seg(name):
    if name not in SEGS:
        SEGS[name] = Seg(name)
    return SEGS[name]


# ---------------------------------------------------------------- per-frame state
G = 520.0     # cm/s^2: a touch floaty so miniature debris reads on screen


def debris(p0, v0, t, spin, floor=BOARD_TOP):
    """Ballistic brick with a couple of damped bounces on the board, in Blender local cm."""
    p, v = Vector(p0), Vector(v0)
    tt, rot = 0.0, 0.0
    dt = 1 / 240
    while tt < t:
        step = min(dt, t - tt)
        v.z -= G * step
        p += v * step
        if p.z < floor + 0.35 and v.z < 0:
            p.z = floor + 0.35
            v.z = -v.z * 0.32
            v.x *= 0.6
            v.y *= 0.6
            spin *= 0.6
        rot += spin * step
        tt += step
    return p, rot


def apply(R, segname, t, shot, u):
    S = seg(segname)
    st = S.at(t)
    M = R["M"]
    playing = st["phase"] == "p"

    # --- AR spawn (reveal shot only): holo sweep outward from the board centre
    reveal = shot["id"] == "reveal"
    spawn_t = t if reveal else 99.0

    def spawn(o, delay, dist):
        if not reveal:
            return 1.0, 0.0
        k = (spawn_t - 0.25 - delay - dist / 55.0) / 0.45
        return clamp(k, 0, 1), clamp(1.0 - (spawn_t - 0.25 - delay - dist / 55.0 - 0.3) / 0.6, 0, 1)

    def fx(o, crack=0.0, holo=0.0, vis=1.0, flash=None):
        o.color = (crack if flash is None else flash, holo, vis, 1)

    for o in R["board"]:
        k, h = spawn(o, 0.0, 0)
        fx(o, 0, h, 1 if k > 0 else 0)
        if o.name == "Marker":
            fx(o, 0.6 + 0.4 * math.sin(t * 3), 0, 1 if k > 0 else 0, flash=0.3 + 0.3 * math.sin(t * 3))
    ring = R["scan"]
    if reveal and 0.2 < spawn_t < 2.4:
        rr = (spawn_t - 0.2) * 32
        ring.hide_render = False
        ring.location = (0, 0, BOARD_TOP + 0.3)
        ring.scale = (rr, rr, 20)
        fx(ring, 0, 0, clamp(1.4 - (spawn_t - 0.2) / 2.0, 0, 1), flash=0)
    else:
        ring.hide_render = True

    # --- castles
    for c in R["castles"]:
        side = c.side
        for o in c.parts:
            d = (Vector(o.matrix_world.translation) / U).length if o.parent is None or o.parent == ROOT else 30
            k, h = spawn(o, 0.35, d)
            if o in c.crown_parts:
                continue
            fx(o, 0, h, 1 if k > 0 else 0, flash=None)
            if o.name.startswith("Rail"):
                fx(o, 0, 0, 1 if k > 0 else 0, flash=0.15 + 0.1 * math.sin(t * 4 + side))
        # shield
        s = st["sh0"] if side == 0 else st["sh1"]
        x, z, flank = rail(s, side)
        c.shield.location = P(x, BOARD_TOP, z)
        k = 1 if side == 0 else -1
        c.shield.rotation_euler = (0, 0, (math.pi / 2 if flank else 0) + (0 if side == 0 else math.pi) * (0 if flank else 1)
                                   + (math.pi if (flank and x > 0) == (side == 0) else 0) * (1 if flank else 0))
        flash = 0.0
        for e in S.ev:
            if e["kind"] == "shield" and e["side"] == side and 0 <= t - e["t"] < 0.35:
                flash = max(flash, math.exp(-(t - e["t"]) * 11))
        ks, hs = spawn(c.pane, 0.9, 20)
        fx(c.pane, 0, 0, (1 if ks > 0 else 0) * (0.25 + 0.75 * smooth(ks)), flash=flash)
        fx(c.emitter, 0, hs, 1 if ks > 0 else 0)
        # flags
        for fl, base, sgn in c.flags:
            me = fl.data
            for v, b in zip(me.vertices, base):
                a = b.x / 2.5
                v.co = Vector((b.x, 0.45 * a * math.sin(t * 7.5 - b.x * 2.3 + side) + 0.15 * a * math.sin(t * 13 + b.z * 3), b.z - 0.25 * a * a))
            fl.rotation_euler = (0, 0, math.radians(30 if side == 0 else 210) + 0.08 * math.sin(t * 1.3))
        # crown: blown off its pedestal when this side loses
        win = S.win
        lost = win and win["side"] == side and t >= win["t"]
        for o in c.crown_parts:
            k2, h2 = spawn(o, 0.5, 28)
            fx(o, 0, h2, 1 if k2 > 0 else 0)
        if lost:
            tt = t - win["t"]
            c.crown.location = c.crown_home + Vector((3 * tt, (-9 if side == 0 else 9) * tt * 0.4, 26 * tt - 0.5 * G * 0.55 * tt * tt))
            if c.crown.location.z < BOARD_TOP + 0.5:
                c.crown.location.z = BOARD_TOP + 0.5
            c.crown.rotation_euler = (5.5 * tt, 3.2 * tt, 1.4 * tt)
            for i, b in enumerate(c.banners):
                fall = smooth(clamp((tt - 0.25 - 0.12 * i) / 0.55, 0, 1))
                b.rotation_euler = (math.radians(-100 * fall) * (1 if side == 0 else 1), math.radians(12 * fall * (1 if i else -1)), 0 if side == 0 else math.pi)
                b.location.z = (3.5 - 2.9 * fall ** 2.5)
        else:
            c.crown.location = c.crown_home + Vector((0, 0, 0.25 * math.sin(t * 2.1 + side)))
            c.crown.rotation_euler = (0, 0, t * 0.6)
            for b in c.banners:
                b.rotation_euler = (0.03 * math.sin(t * 1.7 + b.location.x), 0, 0 if side == 0 else math.pi)
                b.location.z = 3.5

    # --- walls
    for wd in R["walls"]:
        w = wd["w"]
        idx = w["index"]
        hp = S.hp(idx, t)
        br = S.breaks(idx)
        home_c = P(w["x"], 2.0, w["z"])
        dist = home_c.length
        rng = random.Random(idx * 101)
        for n, b in enumerate(wd["bricks"]):
            o = b["o"]
            k, h = spawn(o, 0.2 + 0.02 * b["row"], dist)
            ev = next((e for e in br if (b["stage"] == 1 and e[1] == 1) or (e[1] == 0)), None)
            # which break event releases this brick?
            rel = None
            for te, stage, ix, iz in br:
                if stage == 1 and b["stage"] == 1:
                    rel = (te, ix, iz, stage)
                    break
                if stage == 0:
                    rel = (te, ix, iz, stage)
                    break
            crack = 0.0
            if hp == 1 and b["stage"] == 0:
                t1 = next((e[0] for e in br if e[1] == 1), t)
                crack = 0.35 + 0.65 * math.exp(-(t - t1) * 1.5)
            if rel and t >= rel[0]:
                te, ix, iz, stage = rel
                tt = t - te
                r2 = random.Random(idx * 997 + n)
                if ix is None:          # sudden death: the magic gives way, bricks slump and scatter
                    out = Vector((w["x"], -w["z"], 0)).normalized() if abs(w["x"]) + abs(w["z"]) > 0 else Vector((0, 1, 0))
                    v0 = Vector((r2.uniform(-18, 18), r2.uniform(-18, 18), r2.uniform(8, 38))) + out * r2.uniform(5, 18)
                    tt = max(0.0, tt - 0.05 * b["row"])
                else:
                    src = P(ix, 2.0, iz)
                    d = (b["home"] - src)
                    d.z = 0
                    d = d.normalized() if d.length > 1e-3 else Vector((0, 0, 1))
                    # push away from the fireball's side of the wall (toward the castle interior / back)
                    push = Vector((0, -1 if w["side"] == 0 else 1, 0)) if w["hx"] > w["hz"] else Vector((-1 if w["x"] < 0 else 1, 0, 0))
                    push = -push if (src - b["home"]).dot(push) > 0 else push
                    v0 = push * r2.uniform(20, 55) + d * r2.uniform(5, 22) + Vector((r2.uniform(-10, 10), r2.uniform(-10, 10), r2.uniform(22, 60)))
                spin = r2.uniform(-14, 14)
                p, rot = debris(b["home"], v0, tt, spin)
                life = 1.0 - smooth((tt - 1.3) / 0.45)
                o.location = p
                o.rotation_euler = (b["rot"].x + rot, b["rot"].y + rot * 0.7, b["rot"].z + rot * 0.3)
                o.scale = tuple(sv for sv in o.scale)
                fx(o, 0.5 * math.exp(-tt * 2), 0, 1 if life > 0.02 else 0)
                o.hide_render = life <= 0.02
                if not o.hide_render and life < 1:
                    o["_s"] = o.get("_s", list(o.scale))
                    o.scale = tuple(v * life for v in o["_s"])
                elif "_s" in o and life >= 1:
                    o.scale = tuple(o["_s"])
            else:
                o.hide_render = k <= 0
                o.location = b["home"]
                o.rotation_euler = b["rot"]
                if "_s" in o:
                    o.scale = tuple(o["_s"])
                fx(o, crack, h, 1)

    # --- fireball, trail, light
    fb = R["fireball"]
    serve_ok = any(sv <= t for sv in S.serves) or segname == "B"
    show_ball = playing and serve_ok
    lo = R["fire_light"]
    if show_ball:
        pos = P(st["x"], 2.0, st["z"])
        fb.location = pos
        fb.hide_render = False
        for ch in fb.children:
            ch.hide_render = False
        fb.rotation_euler = (t * 3, t * 4, 0)
        R["fire_noise"].inputs["W"].default_value = t * 2.6
        lo.location = W(pos + Vector((0, 0, 0.2)))
        lo.data.energy = 6.0 + 1.5 * math.sin(t * 37) * math.sin(t * 23)
        lo.hide_render = False
    else:
        fb.hide_render = True
        for ch in fb.children:
            ch.hide_render = True
        lo.hide_render = True
    t_serve = max([sv for sv in S.serves if sv <= t], default=-9)
    for i, o in enumerate(R["trail"]):
        tt = t - (i + 1) * 0.011
        ok = show_ball and tt > t_serve and S.at(tt)["phase"] == "p"
        o.hide_render = not ok
        if ok:
            q = S.at(tt)
            o.location = P(q["x"], 2.0, q["z"])
            r = 1.05 * (1 - i / len(R["trail"])) ** 0.9
            o.scale = (r, r, r)
            fx(o, 0, 0, (1 - i / len(R["trail"])) ** 1.5, flash=-0.2 * i / len(R["trail"]))
    # embers shed along the path
    for i, o in enumerate(R["embers"]):
        age = (i * 0.037 + (t * 0.9) % 0.037 * 0) % 1.1
        ts = math.floor((t - age) * 36) / 36
        a2 = t - ts
        ok = show_ball and ts > t_serve and S.at(ts)["phase"] == "p" and a2 < 1.1
        o.hide_render = not ok
        if ok:
            q = S.at(ts)
            r2 = random.Random(int(ts * 36) * 31 + i)
            o.location = P(q["x"] + r2.uniform(-0.6, 0.6) + r2.uniform(-2, 2) * a2, 2.0 + 4.5 * a2 + r2.uniform(-0.4, 0.4), q["z"] + r2.uniform(-0.6, 0.6) + r2.uniform(-2, 2) * a2)
            r = 0.13 * (1 - a2 / 1.1)
            o.scale = (r, r, r)
            fx(o, 0, 0, 1, flash=0)

    # --- sparks, dust, impact light
    active = []
    for n, e in enumerate(S.ev):
        if e["kind"] in ("shield", "stone", "win", "sudden") and 0 <= t - e["t"] < (2.2 if e["kind"] == "win" else 0.7):
            active.append((n, e))
    si, di = 0, 0
    il = R["impact_light"]
    il.hide_render = True
    best = 0.0
    for n, e in active[-8:]:
        age = t - e["t"]
        kind = e["kind"]
        if kind == "sudden":
            continue
        cnt = {"shield": 14, "stone": 10, "win": 70}[kind]
        rr = random.Random(n * 13 + 7)
        base = P(e["x"], 2.0, e["z"])
        if kind == "win":
            k = 1 if e["side"] == 0 else -1
            base = P(0, 4.5, k * 25)
        for j in range(cnt):
            if si >= len(R["sparks"]):
                break
            if kind == "win":
                v = Vector((rr.uniform(-1, 1), rr.uniform(-1, 1), rr.uniform(0.6, 1.6))).normalized() * rr.uniform(25, 70)
            else:
                v = Vector((rr.uniform(-1, 1), rr.uniform(-1, 1), rr.uniform(0.2, 1.2))).normalized() * rr.uniform(15, 45)
            life = (1.8 if kind == "win" else 0.5) * rr.uniform(0.5, 1.0)
            if age > life:
                continue
            p = base + v * age + Vector((0, 0, -0.5 * G * 0.7 * age * age))
            if p.z < BOARD_TOP:
                continue
            o = R["sparks"][si]
            si += 1
            o.hide_render = False
            o.location = p
            r = (0.16 if kind != "win" else 0.2) * (1 - age / life)
            o.scale = (r * 2.2, r, r)
            o.rotation_euler = v.to_track_quat("X", "Z").to_euler()
            fx(o, 0, 0, 1, flash=0)
        if kind == "stone":
            for j in range(2):
                if di >= len(R["dust"]):
                    break
                o = R["dust"][di]
                di += 1
                if age > 0.9:
                    o.hide_render = True
                    continue
                o.hide_render = False
                r = 0.35 + 1.3 * (1 - math.exp(-age * 4))
                o.location = base + Vector((rr.uniform(-1, 1), rr.uniform(-1, 1), 0.3 + 2.5 * age))
                o.scale = (r, r, r * 0.8)
                fx(o, 0, 0, 0.22 * (1 - age / 0.9))
        strength = math.exp(-age * (5 if kind == "win" else 14)) * (40 if kind == "win" else 8)
        if strength > best:
            best = strength
            il.hide_render = False
            il.location = W(base + Vector((0, 0, 1.5)))
            il.data.energy = strength
            il.data.color = (1.0, 0.55, 0.2) if kind != "shield" else lin(TEAM[e["side"]])
    for o in R["sparks"][si:]:
        o.hide_render = True
    for o in R["dust"][di:]:
        o.hide_render = True

    # --- winner crest rising over the arena
    wc = R["winner"]
    win = S.win
    if win and t > win["t"] + 0.35:
        tt = t - win["t"] - 0.35
        k = back_out(tt / 0.7)
        wc.hide_render = False
        wc.location = P(0, 8 + 7 * smooth(tt / 1.2), 0)
        wc.scale = (k, k, k)
        wc.rotation_euler = (0, 0, tt * 0.8)
        # face the camera from the long edge: stand the crest up
        wc.rotation_euler = (0, 0, 0)
        wc.rotation_euler.rotate(Euler((0, 0, tt * 0.9)))
        fx(wc, 0, 0, clamp(tt / 0.3, 0, 1), flash=0.4 * math.exp(-tt * 3))
    else:
        wc.hide_render = True

    # --- sudden death mood
    R["doom"].energy = 0.0
    if st["elapsed"] >= 75.0 and segname == "B":
        pulse = 0.5 + 0.5 * math.sin(t * 6)
        R["doom"].energy = 70 + 60 * pulse
        R["key"].energy = 170
    else:
        R["key"].energy = 380

    # --- control panel + hand: only in the shots about the built control / solo seat
    pn = R["panel"]
    show_panel = shot["id"] in ("flank", "solo", "reveal", "serve")
    for o in pn["parts"]:
        k, h = spawn(o, 1.2, 38)
        o.hide_render = not show_panel or k <= 0
        fx(o, 0, h, 1)
    val = clamp(st["sh0"] / 54, 0, 1)
    # the teal player faces -z (Lens) from +z, so the rail runs right-to-left from their seat
    kx = -2 + 17 * (0.5 - val) * 0.94
    pn["knob"].location = (kx, -0.6, -0.8)
    fx(pn["knob"], 0, 0, 1 if show_panel else 0)
    left = -2 - 8.5
    pn["fill"].location = ((left + kx) / 2, -0.4, -0.8)
    pn["fill"].scale = (max(0.2, kx - left), 0.2, 0.9)
    hand = R["hand"]
    show_hand = shot["id"] in ("flank",)
    for o in R["hand_parts"]:
        o.hide_render = not show_hand
        fx(o, 0, 0, 0.55, flash=0)
    cur = R["cursor"]
    cur.hide_render = not show_hand
    if show_hand:
        pinch = 0.5 + 0.5 * math.sin(t * 2.2)
        r = 1.65 + 0.9 * (1 - pinch)
        cur.location = (kx, -0.9, -0.8)
        cur.scale = (r, r, r)
        fx(cur, 0, 0, 0.9, flash=0.6 * pinch)
    return st


# ---------------------------------------------------------------- cameras
def look(cam, pos_cm, tgt_cm, lens, focus_cm=None, fstop=2.8):
    p, g = W(pos_cm), W(tgt_cm)
    cam.location = p
    cam.rotation_euler = (g - p).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    cam.data.dof.focus_distance = ((W(focus_cm) if focus_cm is not None else g) - p).length
    cam.data.dof.aperture_fstop = fstop * 2.4


def camera(R, shot, u, st, S, t):
    cam = R["cam"]
    sid = shot["id"]
    ball = P(st["x"], 2.0, st["z"])
    e = lambda a, b: a + (b - a) * smooth(u)
    lv = lambda a, b: Vector(a).lerp(Vector(b), smooth(u))
    if sid == "reveal":
        a = math.radians(e(-38, -8))
        r = e(96, 74)
        look(cam, (r * math.sin(a), -r * math.cos(a), e(40, 34)), (0, e(-4, 0), 1.5), e(30, 34), None, 2.2)
    elif sid == "serve":
        look(cam, lv((42, -44, 13), (34, -36, 11)), (0, 0, 2.2), 42, ball if st["phase"] == "p" else (0, 0, 2), 2.0)
    elif sid == "rally":
        # low side dolly that leads the fireball along the board
        yb = st["z"] * -1
        look(cam, (46, e(-18, 10) + 0.25 * yb, 7.5), (0, 0.55 * yb, 2.0), 34, ball, 2.4)
    elif sid == "walls":
        idx = shot.get("focus_wall")
        wx, wz = shot.get("focus_xz", (0, 18))
        c = P(wx, 2.0, wz)
        k = 1 if wz > 0 else -1
        look(cam, c + Vector((e(14, 10), k * e(19, 15), e(8, 6))), c + Vector((0, 0, 0.5)), 45, c, 2.0)
    elif sid == "flank":
        look(cam, lv((6, -78, 38), (-2, -72, 34)), (-3, -16, 0), 30, P(-8, 2, 18), 2.8)
    elif sid == "solo":
        look(cam, lv((12, -70, 32), (6, -66, 30)), (0, 2, 0), 30, (0, 0, 0), 3.2)
    elif sid == "friend":
        look(cam, lv((-10, 70, 32), (-4, 66, 30)), (0, -2, 0), 30, (0, 0, 0), 3.2)
    elif sid == "sudden":
        a = math.radians(e(20, 55))
        look(cam, (58 * math.sin(a), -58 * math.cos(a), e(60, 52)), (0, 0, 0), 34, (0, 0, 0), 3.5)
    elif sid == "crown":
        crown = P(0, 3.5, 26)
        look(cam, lv((7, -6, 4.2), (5, -9, 4.6)), crown + Vector((0, 0, 1.4)), 30, crown, 2.6)
    elif sid == "specs":
        a = math.radians(e(-150, -95))
        look(cam, (104 * math.sin(a), -104 * math.cos(a), e(52, 42)), (0, 0, 2), 36, (0, 0, 0), 2.8)


# ---------------------------------------------------------------- render
def render_setup(sc, samples=48):
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            pass
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    try:
        sc.view_settings.view_transform = "AgX"
        for look_name in ("AgX - Punchy", "Punchy", "AgX - Medium High Contrast"):
            try:
                sc.view_settings.look = look_name
                break
            except TypeError:
                pass
    except TypeError:
        sc.view_settings.view_transform = "Filmic"
    ee = sc.eevee
    ee.taa_render_samples = samples
    for attr, val in (("use_raytracing", True), ("use_shadows", True), ("shadow_ray_count", 2), ("shadow_step_count", 8),
                      ("use_gtao", True), ("gtao_distance", 0.05), ("use_volumetric_shadows", False)):
        try:
            setattr(ee, attr, val)
        except Exception:
            pass
    try:
        ee.ray_tracing_options.resolution_scale = "1"
    except Exception:
        pass
    sc.render.film_transparent = False


def sim_time(shot, v):
    m = shot["map"]
    if v <= m[0][0]:
        return m[0][1]
    for (va, sa), (vb, sb) in zip(m, m[1:]):
        if va <= v <= vb:
            return sa + (sb - sa) * (v - va) / (vb - va)
    return m[-1][1]


def prepare_shots():
    shots = EDL["shots"]
    for sh in shots:
        if sh["id"] == "walls":
            S = seg(sh["seg"])
            lo, hi = sh["map"][0][1], sh["map"][-1][1]
            ev = [e for e in S.ev if e["kind"] == "stone" and lo <= e["t"] <= hi]
            down = [e for e in ev if e["hp"] == 0] or ev
            if down:
                w = next(w for w in lens_walls() if w["index"] == down[0]["index"])
                sh["focus_wall"], sh["focus_xz"] = w["index"], (w["x"], w["z"])
    return shots


def run(which, still_k=None):
    sc, R = build()
    render_setup(sc, 16 if still_k is not None else 64)
    shots = prepare_shots()
    meta = {}
    for sh in shots:
        if which and sh["id"] not in which:
            continue
        n = round((sh["v1"] - sh["v0"]) * FPS)
        ks = [still_k if still_k >= 0 else n // 2] if still_k is not None else range(n)
        for k in ks:
            k = min(k, n - 1)
            v = sh["v0"] + k / FPS
            t = sim_time(sh, v)
            st = apply(R, sh["seg"], t, sh, k / max(1, n - 1))
            camera(R, sh, k / max(1, n - 1), st, seg(sh["seg"]), t)
            bpy.context.view_layer.update()
            key = f"{sh['id']}_{k:04d}"
            meta[key] = dict(t=round(t, 4), phase=st["phase"], elapsed=round(st["elapsed"], 3), sh0=round(st["sh0"], 3),
                             clock=round(st["clock"], 3), ball=project(sc, R["cam"], W(P(st["x"], 2.0, st["z"]))))
            out = os.path.join(BUILD, f"still_{sh['id']}.png") if still_k is not None else os.path.join(FRAMES, key + ".png")
            if still_k is None and os.path.exists(out):
                continue
            sc.render.filepath = out
            bpy.ops.render.render(write_still=True)
        print(f"[render] {sh['id']} done", flush=True)
    path = os.path.join(BUILD, "frame_meta.json")
    old = json.load(open(path)) if os.path.exists(path) else {}
    old.update(meta)
    json.dump(old, open(path, "w"))


def project(sc, cam, p):
    from bpy_extras.object_utils import world_to_camera_view
    v = world_to_camera_view(sc, cam, p)
    return [round(v.x * 1280, 1), round((1 - v.y) * 720, 1), v.z > 0]


if MODE == "still":
    which = set(ARGS[1].split(",")) if len(ARGS) > 1 and ARGS[1] != "all" else None
    run(which, int(ARGS[2]) if len(ARGS) > 2 else -1)
elif MODE == "render":
    run(set(ARGS[1].split(",")) if len(ARGS) > 1 else None)
