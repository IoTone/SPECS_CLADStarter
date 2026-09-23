import bpy, math, os, sys
from mathutils import Vector

ASSETS = "/Users/dkords/dev/projects/iotone/SPECS_CladStarter/Assets/GeneratedMeshes"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders")
os.makedirs(OUT, exist_ok=True)

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            pass
    sc.render.film_transparent = True
    sc.render.resolution_x = 720
    sc.render.resolution_y = 720
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    w = bpy.data.worlds.new("W")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (1, 1, 1, 1)
    bg.inputs[1].default_value = 0.55
    sc.world = w
    return sc

def load(name):
    bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, name + ".glb"))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    # boost materials: no specular glare, keep base colors punchy
    for o in meshes:
        for slot in o.material_slots:
            m = slot.material
            if not m or not m.use_nodes:
                continue
            for n in m.node_tree.nodes:
                if n.type == "BSDF_PRINCIPLED":
                    n.inputs["Roughness"].default_value = 1.0
                    if "Specular IOR Level" in n.inputs:
                        n.inputs["Specular IOR Level"].default_value = 0.0
    mn = Vector((1e9, 1e9, 1e9)); mx = Vector((-1e9, -1e9, -1e9))
    for o in meshes:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
    return (mn + mx) / 2, (mx - mn).length

def lights():
    for rot, energy in (((50, 10, 35), 4.0), ((60, 0, -140), 1.5)):
        d = bpy.data.lights.new("Sun", "SUN")
        d.energy = energy
        d.angle = 0.2
        o = bpy.data.objects.new("Sun", d)
        o.rotation_euler = [math.radians(a) for a in rot]
        bpy.context.scene.collection.objects.link(o)

def camera(center, size):
    cd = bpy.data.cameras.new("Cam")
    cd.type = "ORTHO"
    cd.ortho_scale = size * 1.05
    cam = bpy.data.objects.new("Cam", cd)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam

def aim(cam, center, size, yaw, pitch):
    r = size * 3
    y, p = math.radians(yaw), math.radians(pitch)
    cam.location = center + Vector((r * math.sin(y) * math.cos(p), -r * math.cos(y) * math.cos(p), r * math.sin(p)))
    d = center - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

def shoot(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

job = sys.argv[sys.argv.index("--") + 1]
name, mode = job.split(":")
sc = reset()
center, size = load(name)
lights()
cam = camera(center, size)
if mode == "probe":
    for yaw in (0, 90, 180, 270):
        aim(cam, center, size, yaw, 10)
        shoot(os.path.join(OUT, f"{name}_probe_{yaw}.png"))
elif mode == "turn":
    base = float(sys.argv[sys.argv.index("--") + 2])
    for i in range(48):
        aim(cam, center, size, base + i * 7.5, 18)
        shoot(os.path.join(OUT, f"{name}_turn_{i:03d}.png"))
else:
    yaw, pitch = map(float, mode.split(","))
    aim(cam, center, size, yaw, pitch)
    shoot(os.path.join(OUT, f"{name}_{int(yaw)}_{int(pitch)}.png"))
