import bpy, bmesh, math, sys, os
from math import radians
from mathutils import Vector

SEG = 80
CELL = 5
NCELL = SEG // CELL

def mat(name, color, rough, metal=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
        out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if out is None:
            out = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(bsdf.outputs[0], out.inputs['Surface'])
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    m.diffuse_color = (*color, 1.0)
    return m

def obj_from_bm(bm, name, material):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    me.materials.append(material)
    return o

def radial(v):
    d = math.hypot(v.co.x, v.co.z)
    return d

def tire_bm():
    bm = bmesh.new()
    prof = [
        (0.240, -0.112),
        (0.300, -0.160),
        (0.355, -0.163),
        (0.405, -0.140),
        (0.424, -0.100),
        (0.428, -0.060),
        (0.430, 0.000),
        (0.428, 0.060),
        (0.424, 0.100),
        (0.405, 0.140),
        (0.355, 0.163),
        (0.300, 0.160),
        (0.240, 0.112),
        (0.236, 0.070),
        (0.234, 0.000),
        (0.236, -0.070),
    ]
    verts = []
    for (r, y) in prof:
        verts.append(bm.verts.new((r, y, 0.0)))
    ring = verts + [verts[0]]
    edges = [bm.edges.new((ring[i], ring[i + 1])) for i in range(len(ring) - 1)]
    bmesh.ops.spin(
        bm, geom=bm.verts[:] + edges,
        axis=(0, 1, 0), cent=(0, 0, 0),
        angle=math.tau, steps=SEG, use_duplicate=False,
    )
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.0006)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    two_pi = math.tau
    cell_faces = {}
    lug_faces = {}
    for f in bm.faces:
        c = f.calc_center_median()
        r = math.hypot(c.x, c.z)
        if r > 0.416 and abs(c.y) < 0.105:
            u = math.atan2(c.z, c.x) % two_pi
            iu = int(u / (two_pi / NCELL)) % NCELL
            row = 0 if c.y < 0 else 1
            cell_faces.setdefault((iu, row), []).append(f)
        elif 0.388 < r <= 0.424 and abs(c.y) >= 0.100:
            side = 0 if c.y < 0 else 1
            u = math.atan2(c.z, c.x) % two_pi
            iu = int(u / (two_pi / NCELL)) % NCELL
            lug_faces.setdefault((iu, side), []).append(f)

    for (iu, row), faces in sorted(cell_faces.items()):
        bmesh.ops.inset_region(bm, faces=faces, thickness=0.013, depth=0.022, use_even_offset=True)

    for (iu, side), faces in sorted(lug_faces.items()):
        if iu % 2 != side:
            continue
        bmesh.ops.inset_region(bm, faces=faces, thickness=0.014, depth=0.018, use_even_offset=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def spoke(bm, ang, r0, r1, w0, w1, depth, ycen=0.0):
    ca, sa = math.cos(ang), math.sin(ang)
    def P(r, w, y):
        return bm.verts.new((ca * r - sa * w, y, sa * r + ca * w))
    y0, y1 = ycen - depth / 2, ycen + depth / 2
    a = P(r0, w0, y0); b = P(r1, w1, y0); c = P(r1, -w1, y0); d = P(r0, -w0, y0)
    e = P(r0, w0, y1); f = P(r1, w1, y1); g = P(r1, -w1, y1); h = P(r0, -w0, y1)
    bm.faces.new((a, b, f, e))
    bm.faces.new((d, h, g, c))
    bm.faces.new((a, e, h, d))
    bm.faces.new((b, c, g, f))
    bm.faces.new((a, d, c, b))
    bm.faces.new((e, f, g, h))

def tube(bm, r, y0, y1, seg=48, rr=None, z_off=0.0):
    rr = rr or r
    vs0 = [bm.verts.new((rr * math.cos(i / seg * math.tau), y0, rr * math.sin(i / seg * math.tau) + z_off)) for i in range(seg)]
    vs1 = [bm.verts.new((r * math.cos(i / seg * math.tau), y1, r * math.sin(i / seg * math.tau) + z_off)) for i in range(seg)]
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((vs0[i], vs0[j], vs1[j], vs1[i]))
    return vs0, vs1

def disc(bm, vs, center, flip=False):
    c = bm.verts.new(center)
    for i in range(len(vs)):
        j = (i + 1) % len(vs)
        if flip:
            bm.faces.new((c, vs[j], vs[i]))
        else:
            bm.faces.new((c, vs[i], vs[j]))

def rim_bm():
    bm = bmesh.new()
    vs0, vs1 = tube(bm, 0.238, -0.100, 0.085, seg=64)
    disc(bm, vs0, (0, -0.100, 0), flip=True)
    for i in range(10):
        ang = i / 10 * math.tau + math.radians(6)
        spoke(bm, ang, 0.105, 0.195, 0.030, 0.026, 0.050, ycen=0.080)
    vs2, vs3 = tube(bm, 0.105, -0.050, 0.040, seg=32)
    disc(bm, vs3, (0, 0.040, 0))
    vs4, vs5 = tube(bm, 0.058, 0.040, 0.128, seg=24)
    disc(bm, vs5, (0, 0.122, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def ring_bm():
    bm = bmesh.new()
    seg = 64
    r_in, r_out, y0, y1 = 0.200, 0.234, 0.085, 0.115
    loops = []
    for r in (r_in, r_out):
        for y in (y0, y1):
            loops.append([bm.verts.new((r * math.cos(i / seg * math.tau), y, r * math.sin(i / seg * math.tau))) for i in range(seg)])
    rin0, rin1, rout0, rout1 = loops
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((rout0[i], rout0[j], rout1[j], rout1[i]))
        bm.faces.new((rin1[i], rin1[j], rin0[j], rin0[i]))
        bm.faces.new((rin0[i], rin0[j], rout0[j], rout0[i]))
        bm.faces.new((rout1[i], rout1[j], rin1[j], rin1[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def box(bm, x0, x1, y0, y1, z0, z1, mi=0):
    pts = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
           (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    v = [bm.verts.new(p) for p in pts]
    for idx in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5)):
        f = bm.faces.new(tuple(v[i] for i in idx))
        f.material_index = mi
    return v

M_HOUS, M_WARM, M_AMBER, M_WHITE, M_RED = 0, 1, 2, 3, 4

def obj_from_bm_m(bm, name, mats):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    for m in mats:
        me.materials.append(m)
    return o

def mirror_object(o, name):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.scale(bm, verts=bm.verts[:], vec=(1.0, -1.0, 1.0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    for m in o.data.materials:
        me.materials.append(m)
    return obj

def led_bar_bm():
    """Замена SM_KAMAZ_Pickup_Light_Top: LED-балка, свет в -X (назад), тёплый тон.
    Донорская рамка: пивот 0, Y +-0.126 у донора, балка 48 см."""
    bm = bmesh.new()
    box(bm, -0.055, 0.005, -0.240, 0.240, -0.055, 0.055, M_HOUS)
    seg_w, gap, n = 0.038, 0.014, 8
    pitch = seg_w + gap
    ys = -(n * seg_w + (n - 1) * gap) / 2
    for i in range(n):
        a = ys + i * pitch
        box(bm, -0.057, -0.048, a, a + seg_w, -0.026, 0.026, M_WARM)
    for i in range(n - 1):
        a = ys + i * pitch + seg_w
        box(bm, -0.052, -0.042, a, a + gap, -0.030, 0.030, M_HOUS)
    box(bm, -0.057, -0.048, -0.238, -0.205, -0.030, 0.030, M_AMBER)
    box(bm, -0.057, -0.048, 0.205, 0.238, -0.030, 0.030, M_AMBER)
    box(bm, -0.025, 0.000, 0.150, 0.190, -0.078, -0.055, M_HOUS)
    box(bm, -0.025, 0.000, -0.190, -0.150, -0.078, -0.055, M_HOUS)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def headlight_bm():
    """Замена SM_KAMAZ_Pickup_Lights_FrontLeft: левый (outboard = -Y), рамка донора
    X 0..0.48, Y -0.228..0.146, Z -0.117..0.078. Квадратные прожекторы + C-DRL,
    C раскрывается наружу, поворотник amber у бортика."""
    bm = bmesh.new()
    box(bm, 0.010, 0.055, -0.225, 0.140, -0.110, 0.070, M_HOUS)
    box(bm, 0.010, 0.300, -0.225, 0.140, 0.058, 0.070, M_HOUS)
    box(bm, 0.010, 0.300, -0.225, 0.140, -0.110, -0.098, M_HOUS)
    box(bm, 0.010, 0.300, -0.225, -0.213, -0.098, 0.058, M_HOUS)
    box(bm, 0.010, 0.300, 0.128, 0.140, -0.098, 0.058, M_HOUS)
    box(bm, 0.240, 0.262, -0.213, 0.128, -0.098, 0.058, M_HOUS)
    box(bm, 0.262, 0.300, -0.190, -0.050, -0.005, 0.050, M_WARM)
    box(bm, 0.262, 0.300, -0.190, -0.070, -0.095, -0.045, M_WARM)
    box(bm, 0.250, 0.282, -0.200, 0.125, 0.052, 0.072, M_WHITE)
    box(bm, 0.250, 0.282, -0.200, 0.125, -0.116, -0.100, M_WHITE)
    box(bm, 0.250, 0.282, 0.103, 0.125, -0.098, 0.072, M_WHITE)
    box(bm, 0.262, 0.284, 0.058, 0.100, -0.048, 0.030, M_AMBER)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def taillight_bm():
    """Замена SM_KAMAZ_Pickup_Light_BackLeft: левый (outboard = -Y), рамка донора
    X -0.232..0, Y -0.018..0.142, Z -0.28..0.155. Задняя панель силуэта ниши +
    C-фонарь (красный C раскрывается наружу), ходовой белый, поворотник amber."""
    bm = bmesh.new()
    box(bm, -0.020, 0.002, -0.018, 0.142, -0.280, 0.155, 0)
    box(bm, -0.050, 0.000, -0.018, 0.142, 0.115, 0.150, 1)
    box(bm, -0.050, 0.000, -0.018, 0.142, 0.000, 0.035, 1)
    box(bm, -0.050, 0.000, 0.105, 0.142, 0.000, 0.150, 1)
    box(bm, -0.042, -0.020, 0.050, 0.105, 0.035, 0.115, 1)
    box(bm, -0.042, -0.020, -0.012, 0.050, 0.035, 0.075, 2)
    box(bm, -0.046, -0.026, 0.058, 0.100, -0.034, 0.000, 3)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)

def export_one(o, path):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_yup=True, use_selection=True)
    print(f"exported {path}")

def setup_render():
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.type = 'ORTHO'
    cam_data.clip_start = 0.01
    cam_data.clip_end = 100.0
    cam = bpy.data.objects.new("Cam", cam_data)
    bpy.context.collection.objects.link(cam)
    tgt = bpy.data.objects.new("Tgt", None)
    bpy.context.collection.objects.link(tgt)
    con = cam.constraints.new('TRACK_TO')
    con.target = tgt
    con.track_axis = 'TRACK_NEGATIVE_Z'
    con.up_axis = 'UP_Y'
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_cavity = True
    scene.display.shading.show_shadows = True
    scene.render.resolution_x = 800
    scene.render.resolution_y = 800
    scene.camera = cam
    return cam, tgt

def render_views(cam, tgt, center, views, out, prefix):
    for name, (direction, ortho) in views.items():
        d = direction.normalized()
        cam.location = center + d * 2.0
        cam.data.ortho_scale = ortho
        tgt.location = center
        scene = bpy.context.scene
        scene.render.filepath = os.path.join(out, f"{prefix}_{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"rendered {prefix}_{name}")

def build_wheel(out):
    m_tire = mat("KAMAZ_Tire", (0.045, 0.045, 0.048), 0.95)
    m_rim = mat("KAMAZ_RimDark", (0.05, 0.05, 0.055), 0.55, metal=0.65)
    m_red = mat("KAMAZ_AccentRed", (0.55, 0.05, 0.05), 0.45, metal=0.3)

    tire = obj_from_bm(tire_bm(), "SM_KAMAZ_Wheel_Tire", m_tire)
    rim = obj_from_bm(rim_bm(), "SM_KAMAZ_Wheel_Rim", m_rim)
    ring = obj_from_bm(ring_bm(), "SM_KAMAZ_Wheel_AccentRing", m_red)

    total = 0
    for o in (tire, rim, ring):
        t = tris(o)
        total += t
        print(f"[{o.name}] tris={t}")
    print(f"[wheel] total tris={total}")

    bpy.ops.object.select_all(action='DESELECT')
    for o in (tire, rim, ring):
        o.select_set(True)
    bpy.context.view_layer.objects.active = rim
    bpy.ops.object.join()
    wheel = bpy.context.view_layer.objects.active
    wheel.name = "SM_KAMAZ_Pickup_Wheel"

    export_one(wheel, os.path.join(out, "wheel_v5.glb"))

    cam, tgt = setup_render()
    center = Vector((0.0, 0.0, 0.0))
    views = {
        "face": (Vector((0.0, 1.4, 0.25)), 1.25),
        "side": (Vector((1.4, 0.0, 0.25)), 1.25),
        "quarter": (Vector((0.9, 0.9, 0.7)), 1.25),
    }
    render_views(cam, tgt, center, views, out, "wheel_v5")

def build_lights(out):
    m_hous = mat("KAMAZ_HousingDark", (0.030, 0.030, 0.034), 0.50, metal=0.70)
    m_warm = mat("KAMAZ_LensWarm", (1.00, 0.72, 0.40), 0.25)
    m_amber = mat("KAMAZ_AccentAmber", (1.00, 0.45, 0.10), 0.30)
    m_white = mat("KAMAZ_LensWhite", (0.95, 0.96, 1.00), 0.20)
    m_red = mat("KAMAZ_LensRed", (0.62, 0.05, 0.05), 0.30)

    bar = obj_from_bm_m(led_bar_bm(), "SM_KAMAZ_Pickup_Light_Top_Bar", [m_hous, m_warm, m_amber])
    head_l = obj_from_bm_m(headlight_bm(), "SM_KAMAZ_Pickup_Lights_FrontLeft", [m_hous, m_warm, m_amber, m_white])
    head_r = mirror_object(head_l, "SM_KAMAZ_Pickup_Lights_FrontRight")
    tail_l = obj_from_bm_m(taillight_bm(), "SM_KAMAZ_Pickup_Light_BackLeft", [m_hous, m_red, m_white, m_amber])
    tail_r = mirror_object(tail_l, "SM_KAMAZ_Pickup_Light_BackRight")

    for o in (bar, head_l, head_r, tail_l, tail_r):
        print(f"[{o.name}] tris={tris(o)}")

    export_one(bar, os.path.join(out, "lightbar_v1.glb"))
    export_one(head_l, os.path.join(out, "headlight_L_v1.glb"))
    export_one(head_r, os.path.join(out, "headlight_R_v1.glb"))
    export_one(tail_l, os.path.join(out, "taillight_L_v1.glb"))
    export_one(tail_r, os.path.join(out, "taillight_R_v1.glb"))

    cam, tgt = setup_render()
    render_views(cam, tgt, Vector((-0.026, 0.0, 0.0)), {
        "rear": (Vector((-1.0, 0.0, 0.0)), 0.65),
        "quarter": (Vector((-0.75, -0.65, 0.45)), 0.65),
    }, out, "lightbar_v1")
    render_views(cam, tgt, Vector((0.155, -0.045, -0.020)), {
        "front": (Vector((1.0, 0.0, 0.0)), 0.50),
        "quarter": (Vector((0.75, -0.55, 0.35)), 0.50),
    }, out, "headlight_v1")
    render_views(cam, tgt, Vector((-0.030, 0.060, 0.030)), {
        "rear": (Vector((-1.0, 0.0, 0.0)), 0.45),
        "quarter": (Vector((-0.70, -0.55, 0.30)), 0.45),
    }, out, "taillight_v1")

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[0] if argv else r"C:\Users\leman\AppData\Local\Temp\rufp\kamaz\model"
    stage = argv[1] if len(argv) > 1 else "all"
    os.makedirs(out, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)

    if stage in ("wheel", "all"):
        build_wheel(out)
    if stage in ("lights", "all"):
        build_lights(out)
    print("DONE")

main()
