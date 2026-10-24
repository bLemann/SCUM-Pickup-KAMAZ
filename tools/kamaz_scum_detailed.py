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

def obbox(bm, pts, mi=0):
    v = [bm.verts.new(p) for p in pts]
    for idx in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5)):
        f = bm.faces.new(tuple(v[i] for i in idx))
        f.material_index = mi
    return v

def cyl_y(bm, r, y0, y1, cx=0.0, cz=0.0, seg=32, mi=0):
    a = [bm.verts.new((cx + r * math.cos(i / seg * math.tau), y0, cz + r * math.sin(i / seg * math.tau))) for i in range(seg)]
    b = [bm.verts.new((cx + r * math.cos(i / seg * math.tau), y1, cz + r * math.sin(i / seg * math.tau))) for i in range(seg)]
    faces = []
    for i in range(seg):
        j = (i + 1) % seg
        faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    c0 = bm.verts.new((cx, y0, cz))
    c1 = bm.verts.new((cx, y1, cz))
    for i in range(seg):
        j = (i + 1) % seg
        faces.append(bm.faces.new((c0, a[j], a[i])))
        faces.append(bm.faces.new((c1, b[i], b[j])))
    for f in faces:
        f.material_index = mi

def cyl_x(bm, r, x0, x1, cy=0.0, cz=0.0, seg=20, mi=0):
    a = [bm.verts.new((x0, cy + r * math.cos(i / seg * math.tau), cz + r * math.sin(i / seg * math.tau))) for i in range(seg)]
    b = [bm.verts.new((x1, cy + r * math.cos(i / seg * math.tau), cz + r * math.sin(i / seg * math.tau))) for i in range(seg)]
    faces = []
    for i in range(seg):
        j = (i + 1) % seg
        faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    c0 = bm.verts.new((x0, cy, cz))
    c1 = bm.verts.new((x1, cy, cz))
    for i in range(seg):
        j = (i + 1) % seg
        faces.append(bm.faces.new((c0, a[j], a[i])))
        faces.append(bm.faces.new((c1, b[i], b[j])))
    for f in faces:
        f.material_index = mi

def cyl_z(bm, r, z0, z1, cx=0.0, cy=0.0, seg=12, mi=0):
    a = [bm.verts.new((cx + r * math.cos(i / seg * math.tau), cy + r * math.sin(i / seg * math.tau), z0)) for i in range(seg)]
    b = [bm.verts.new((cx + r * math.cos(i / seg * math.tau), cy + r * math.sin(i / seg * math.tau), z1)) for i in range(seg)]
    faces = []
    for i in range(seg):
        j = (i + 1) % seg
        faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    c0 = bm.verts.new((cx, cy, z0))
    c1 = bm.verts.new((cx, cy, z1))
    for i in range(seg):
        j = (i + 1) % seg
        faces.append(bm.faces.new((c0, a[j], a[i])))
        faces.append(bm.faces.new((c1, b[i], b[j])))
    for f in faces:
        f.material_index = mi

def gusset(bm, x, y, zb, zt, dx, th, mi=0):
    y2 = y + th
    a = bm.verts.new((x, y, zb)); b = bm.verts.new((x + dx, y, zt)); c = bm.verts.new((x, y, zt))
    a2 = bm.verts.new((x, y2, zb)); b2 = bm.verts.new((x + dx, y2, zt)); c2 = bm.verts.new((x, y2, zt))
    for f in (bm.faces.new((a, b, c)), bm.faces.new((a2, c2, b2)),
              bm.faces.new((a, b, b2, a2)), bm.faces.new((c, b, b2, c2))):
        f.material_index = mi

def add_text(obj, text, size, loc, rot, mat, extrude=0.003):
    cu = bpy.data.curves.new(text, type='FONT')
    cu.body = text
    cu.size = size
    cu.extrude = extrude
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    to = bpy.data.objects.new("TMP_txt", cu)
    bpy.context.collection.objects.link(to)
    to.location = loc
    to.rotation_euler = rot
    bpy.ops.object.select_all(action='DESELECT')
    to.select_set(True)
    bpy.context.view_layer.objects.active = to
    bpy.ops.object.convert(target='MESH')
    to.data.materials.append(mat)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()

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

def roofrack_bm():
    """Замена SM_KAMAZ_Pickup_RoofRack: кунг-рейка, рамка донора
    X 0.049..1.424, Y +-0.62, Z 0.439..1.156. Квадратная труба 5 см,
    ноги+рейки+поперечины, косынки, площадка LED-балки (Light_Top) спереди,
    красные акцентные пластины."""
    bm = bmesh.new()
    LX0, LX1, LY = 0.11, 1.36, 0.565
    for lx in (LX0, LX1):
        for ly in (-LY, LY):
            box(bm, lx - 0.035, lx + 0.035, ly - 0.035, ly + 0.035, 0.439, 0.459, 0)
            box(bm, lx - 0.025, lx + 0.025, ly - 0.025, ly + 0.025, 0.45, 1.13, 0)
    for ly in (-LY, LY):
        box(bm, 0.08, 1.39, ly - 0.025, ly + 0.025, 0.52, 0.57, 0)
        box(bm, 0.08, 1.39, ly - 0.025, ly + 0.025, 1.08, 1.13, 0)
    box(bm, 0.085, 0.135, -LY - 0.025, LY + 0.025, 1.08, 1.13, 0)
    box(bm, 1.335, 1.385, -LY - 0.025, LY + 0.025, 1.08, 1.13, 0)
    box(bm, 0.50, 0.55, -LY - 0.025, LY + 0.025, 0.52, 0.57, 0)
    box(bm, 0.95, 1.00, -LY - 0.025, LY + 0.025, 0.52, 0.57, 0)
    for lx, dx in ((LX0, 0.14), (LX1, -0.14)):
        for ly in (-LY, LY):
            y0 = (ly - 0.037) if ly > 0 else (ly + 0.025)
            gusset(bm, lx, y0, 1.02, 1.125, dx, 0.012, 1)
    box(bm, 0.05, 0.18, -0.15, 0.15, 1.13, 1.148, 0)
    box(bm, 0.08, 0.12, -0.14, -0.10, 1.148, 1.156, 0)
    box(bm, 0.08, 0.12, 0.10, 0.14, 1.148, 1.156, 0)
    box(bm, 0.30, 0.85, -0.595, -0.585, 1.09, 1.12, 2)
    box(bm, 0.30, 0.85, 0.585, 0.595, 1.09, 1.12, 2)
    box(bm, 0.15, 0.45, -0.595, -0.585, 0.525, 0.565, 2)
    box(bm, 0.15, 0.45, 0.585, 0.595, 0.525, 0.565, 2)
    for ly in (-LY, LY):
        box(bm, 0.09, 1.38, ly - 0.012, ly + 0.012, 0.57, 1.08, 0)
    for i in range(10):
        xb = 0.17 + i * 0.118
        box(bm, xb, xb + 0.014, -0.565, 0.565, 0.795, 0.823, 0)
    for xc in (0.38, 1.04):
        box(bm, xc, xc + 0.014, -0.014, 0.014, 0.57, 0.795, 0)
    for xe in (LX0 - 0.012, LX1 - 0.012):
        for sgn in (1.0, -1.0):
            ya, za = -LY + 0.04, 0.58
            yb, zb = LY - 0.04, 1.078
            if sgn < 0:
                ya, za, yb, zb = yb, zb, ya, za
            obbox(bm, [(xe, ya, za), (xe + 0.024, ya, za), (xe + 0.024, yb, zb), (xe, yb, zb),
                       (xe + 0.024, ya, za - 0.026), (xe + 0.048, ya, za - 0.026),
                       (xe + 0.048, yb, zb - 0.026), (xe + 0.024, yb, zb - 0.026)], 1)
    for lx in (LX0, LX1):
        for ly in (-LY, LY):
            cyl_z(bm, 0.009, 1.128, 1.138, cx=lx, cy=ly, seg=6, mi=1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def seat_bm():
    """Замена SM_KAMAZ_Pickup_Seat_Left: переднее кресло, рамка донора
    X -0.463..0.264, Y -0.282..0.286, Z 0..0.816. Чёрная кожа + красная стёжка."""
    bm = bmesh.new()
    box(bm, -0.40, 0.22, -0.24, -0.16, 0.02, 0.09, 2)
    box(bm, -0.40, 0.22, 0.16, 0.24, 0.02, 0.09, 2)
    box(bm, -0.12, -0.06, -0.24, 0.24, 0.02, 0.09, 2)
    box(bm, -0.42, 0.24, -0.26, 0.26, 0.16, 0.34, 0)
    box(bm, -0.40, 0.20, -0.285, -0.225, 0.16, 0.40, 0)
    box(bm, -0.40, 0.20, 0.225, 0.285, 0.16, 0.40, 0)
    box(bm, -0.38, 0.16, -0.02, 0.02, 0.34, 0.348, 1)
    obbox(bm, [(-0.26, -0.27, 0.34), (-0.26, 0.27, 0.34), (-0.44, 0.27, 0.40), (-0.44, -0.27, 0.40),
               (-0.38, -0.27, 0.72), (-0.38, 0.27, 0.72), (-0.455, 0.27, 0.745), (-0.455, -0.27, 0.745)], 0)
    obbox(bm, [(-0.28, -0.025, 0.40), (-0.28, 0.025, 0.40), (-0.315, 0.025, 0.40), (-0.315, -0.025, 0.40),
               (-0.37, -0.025, 0.71), (-0.37, 0.025, 0.71), (-0.405, 0.025, 0.71), (-0.405, -0.025, 0.71)], 1)
    box(bm, -0.44, -0.35, -0.16, 0.16, 0.73, 0.81, 0)
    box(bm, -0.405, -0.35, -0.16, 0.16, 0.76, 0.775, 1)
    box(bm, -0.42, -0.395, 0.06, 0.10, 0.71, 0.735, 2)
    box(bm, -0.42, -0.395, -0.10, -0.06, 0.71, 0.735, 2)
    box(bm, -0.463, -0.448, -0.25, 0.25, 0.42, 0.74, 2)
    obbox(bm, [(-0.275, -0.27, 0.335), (-0.275, 0.27, 0.335), (-0.455, 0.27, 0.395), (-0.455, -0.27, 0.395),
               (-0.395, -0.27, 0.715), (-0.395, 0.27, 0.715), (-0.47, 0.27, 0.745), (-0.47, -0.27, 0.745)], 2)
    box(bm, -0.402, -0.388, -0.06, -0.02, 0.715, 0.75, 2)
    box(bm, -0.402, -0.388, 0.02, 0.06, 0.715, 0.75, 2)
    box(bm, -0.30, -0.292, -0.25, 0.25, 0.34, 0.348, 1)
    box(bm, 0.08, 0.088, -0.25, 0.25, 0.34, 0.348, 1)
    cyl_y(bm, 0.015, -0.23, 0.23, cx=-0.09, cz=0.055, seg=8, mi=2)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def seat_back_bm():
    """Замена SM_KAMAZ_Pickup_Seat_Back: задняя скамья, рамка донора
    X -0.420..0.300, Y -0.697..0.711, Z 0.005..0.793. Два подголовника + стёжка."""
    bm = bmesh.new()
    box(bm, -0.28, 0.26, -0.60, -0.52, 0.02, 0.10, 2)
    box(bm, -0.28, 0.26, 0.52, 0.60, 0.02, 0.10, 2)
    box(bm, -0.28, 0.26, -0.04, 0.04, 0.02, 0.10, 2)
    box(bm, -0.30, 0.28, -0.62, 0.62, 0.16, 0.36, 0)
    box(bm, 0.265, 0.285, -0.60, 0.60, 0.20, 0.33, 1)
    obbox(bm, [(-0.24, -0.66, 0.36), (-0.24, 0.66, 0.36), (-0.40, 0.66, 0.42), (-0.40, -0.66, 0.42),
               (-0.36, -0.66, 0.70), (-0.36, 0.66, 0.70), (-0.42, 0.66, 0.72), (-0.42, -0.66, 0.72)], 0)
    obbox(bm, [(-0.262, -0.025, 0.44), (-0.262, 0.025, 0.44), (-0.292, 0.025, 0.44), (-0.292, -0.025, 0.44),
               (-0.355, -0.025, 0.70), (-0.355, 0.025, 0.70), (-0.385, 0.025, 0.70), (-0.385, -0.025, 0.70)], 1)
    box(bm, -0.40, -0.32, 0.18, 0.50, 0.715, 0.79, 0)
    box(bm, -0.40, -0.32, -0.50, -0.18, 0.715, 0.79, 0)
    box(bm, -0.365, -0.32, 0.18, 0.50, 0.75, 0.764, 1)
    box(bm, -0.365, -0.32, -0.50, -0.18, 0.75, 0.764, 1)
    box(bm, -0.42, -0.405, -0.64, 0.64, 0.44, 0.72, 2)
    obbox(bm, [(-0.255, -0.66, 0.355), (-0.255, 0.66, 0.355), (-0.415, 0.66, 0.415), (-0.415, -0.66, 0.415),
               (-0.375, -0.66, 0.695), (-0.375, 0.66, 0.695), (-0.435, 0.66, 0.715), (-0.435, -0.66, 0.715)], 2)
    box(bm, -0.365, -0.35, 0.30, 0.36, 0.70, 0.725, 2)
    box(bm, -0.365, -0.35, -0.36, -0.30, 0.70, 0.725, 2)
    box(bm, -0.252, -0.244, -0.62, 0.62, 0.355, 0.363, 1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def alternator_bm():
    """Замена SM_KAMAZ_Pickup_Alternator: генератор, рамка донора
    X 0..0.166, Y -0.135..0.162, Z -0.298..0.101. Корпус-цилиндр по Y,
    шкив, задняя крышка, клеммы, кронштейн вниз."""
    bm = bmesh.new()
    cyl_y(bm, 0.078, -0.05, 0.09, cx=0.083, cz=-0.02, seg=32, mi=0)
    cyl_y(bm, 0.081, -0.02, 0.00, cx=0.083, cz=-0.02, seg=32, mi=0)
    cyl_y(bm, 0.081, 0.03, 0.05, cx=0.083, cz=-0.02, seg=32, mi=0)
    cyl_y(bm, 0.042, -0.135, -0.05, cx=0.083, cz=-0.02, seg=24, mi=1)
    cyl_y(bm, 0.047, -0.105, -0.085, cx=0.083, cz=-0.02, seg=24, mi=1)
    cyl_y(bm, 0.062, 0.09, 0.13, cx=0.083, cz=-0.02, seg=24, mi=0)
    box(bm, 0.063, 0.083, 0.125, 0.16, -0.06, -0.02, 1)
    box(bm, 0.095, 0.115, 0.125, 0.16, -0.01, 0.03, 1)
    box(bm, 0.0, 0.022, -0.09, 0.07, -0.16, 0.06, 1)
    box(bm, 0.0, 0.022, -0.03, 0.03, -0.298, -0.13, 1)
    box(bm, 0.0, 0.02, 0.10, 0.14, -0.10, -0.04, 1)
    cyl_y(bm, 0.081, -0.045, -0.025, cx=0.083, cz=-0.02, seg=32, mi=0)
    cyl_y(bm, 0.081, 0.055, 0.075, cx=0.083, cz=-0.02, seg=32, mi=0)
    cyl_y(bm, 0.047, -0.128, -0.112, cx=0.083, cz=-0.02, seg=24, mi=1)
    cyl_y(bm, 0.047, -0.073, -0.057, cx=0.083, cz=-0.02, seg=24, mi=1)
    cyl_y(bm, 0.016, -0.142, -0.130, cx=0.083, cz=-0.02, seg=6, mi=1)
    cyl_y(bm, 0.026, 0.135, 0.162, cx=0.105, cz=0.01, seg=8, mi=2)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def battery_bm():
    """Замена SM_KAMAZ_Pickup_Battery: АКБ, рамка донора
    X +-0.156, Y +-0.113, Z 0..0.201. Корпус, крышка, рёбра,
    клеммы (+красная), ручка."""
    bm = bmesh.new()
    box(bm, -0.145, 0.145, -0.105, 0.105, 0.0, 0.165, 0)
    box(bm, -0.135, 0.135, -0.095, 0.095, 0.165, 0.172, 0)
    box(bm, 0.085, 0.115, -0.055, -0.025, 0.172, 0.20, 2)
    box(bm, -0.115, -0.085, -0.055, -0.025, 0.172, 0.20, 1)
    box(bm, 0.080, 0.120, -0.060, -0.020, 0.196, 0.205, 2)
    box(bm, -0.06, 0.06, -0.014, 0.014, 0.172, 0.19, 1)
    for x0 in (-0.10, -0.05, 0.0, 0.05):
        box(bm, x0, x0 + 0.03, -0.108, -0.102, 0.03, 0.13, 0)
        box(bm, x0, x0 + 0.03, 0.102, 0.108, 0.03, 0.13, 0)
    for cx6 in (-0.10, -0.06, -0.02, 0.02, 0.06, 0.10):
        cyl_z(bm, 0.014, 0.172, 0.191, cx=cx6, cy=0.055, seg=8, mi=0)
    box(bm, 0.078, 0.122, -0.062, -0.018, 0.196, 0.208, 1)
    box(bm, -0.122, -0.078, -0.062, -0.018, 0.196, 0.208, 1)
    cyl_y(bm, 0.012, -0.108, -0.132, cx=0.10, cz=0.15, seg=6, mi=1)
    cyl_y(bm, 0.012, -0.108, -0.132, cx=-0.10, cz=0.15, seg=6, mi=1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def bumper_front_bm():
    """Замена SK_KAMAZ_Pickup_Bumper_Front: рамка донора
    X -0.324..0.344 (морда +X), Y +-0.987, Z -0.047..0.445.
    Силовой бампер: лицевая плита с ледяной DRL-полосой, крылья,
    металлическая защита, 2 красные проушины, LED-противотуманки."""
    bm = bmesh.new()
    box(bm, -0.10, 0.30, -0.95, 0.95, 0.02, 0.28, 0)
    box(bm, 0.30, 0.34, -0.70, 0.70, 0.10, 0.24, 0)
    box(bm, 0.30, 0.34, -0.70, 0.70, 0.24, 0.28, 3)
    box(bm, -0.05, 0.30, -0.987, -0.80, 0.05, 0.30, 0)
    box(bm, -0.05, 0.30, 0.80, 0.987, 0.05, 0.30, 0)
    box(bm, 0.16, 0.30, -0.72, 0.72, -0.047, 0.02, 1)
    box(bm, 0.20, 0.24, -0.50, -0.38, -0.047, 0.02, 1)
    box(bm, 0.20, 0.24, 0.38, 0.50, -0.047, 0.02, 1)
    box(bm, 0.26, 0.31, -0.87, -0.73, 0.12, 0.24, 0)
    box(bm, 0.31, 0.34, -0.845, -0.755, 0.145, 0.215, 4)
    box(bm, 0.26, 0.31, 0.73, 0.87, 0.12, 0.24, 0)
    box(bm, 0.31, 0.34, 0.755, 0.845, 0.145, 0.215, 4)
    for yc in (-0.32, 0.32):
        box(bm, 0.26, 0.32, yc - 0.05, yc - 0.03, -0.047, 0.05, 2)
        box(bm, 0.26, 0.32, yc + 0.03, yc + 0.05, -0.047, 0.05, 2)
        box(bm, 0.26, 0.32, yc - 0.05, yc + 0.05, 0.03, 0.05, 2)
    box(bm, 0.06, 0.20, -0.28, -0.16, -0.047, -0.005, 0)
    box(bm, 0.06, 0.20, -0.06, 0.06, -0.047, -0.005, 0)
    box(bm, 0.06, 0.20, 0.16, 0.28, -0.047, -0.005, 0)
    box(bm, -0.32, 0.05, -0.55, 0.55, 0.28, 0.33, 0)
    box(bm, -0.10, 0.10, -0.50, -0.40, 0.28, 0.445, 0)
    box(bm, -0.10, 0.10, 0.40, 0.50, 0.28, 0.445, 0)
    for by, bz in ((0.60, 0.13), (0.60, 0.25), (-0.60, 0.13), (-0.60, 0.25), (0.25, 0.25), (-0.25, 0.25)):
        cyl_x(bm, 0.011, 0.338, 0.352, cy=by, cz=bz, seg=6, mi=1)
    box(bm, 0.295, 0.315, -0.16, -0.10, 0.04, 0.07, 4)
    box(bm, 0.295, 0.315, 0.10, 0.16, 0.04, 0.07, 4)
    for yc in (-0.32, 0.32):
        cyl_x(bm, 0.010, 0.255, 0.325, cy=yc, cz=0.0, seg=6, mi=1)
    for yr in (-0.19, -0.15, 0.15, 0.19):
        box(bm, 0.295, 0.315, yr - 0.02, yr + 0.02, -0.047, 0.02, 1)
    box(bm, -0.02, 0.28, -0.987, -0.80, 0.30, 0.315, 2)
    box(bm, -0.02, 0.28, 0.80, 0.987, 0.30, 0.315, 2)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def bumper_back_bm():
    """Замена SK_KAMAZ_Pickup_Bumper_Back: рамка донора
    X -0.198..0.172 (внешняя сторона -X), Y +-0.95, Z -0.121..0.107.
    Силовой бампер: задняя плита, ступенька, козырёк над номером,
    2 красные шаклы с пальцами, квэд-эхауст (4 насадки)."""
    bm = bmesh.new()
    box(bm, -0.14, 0.172, -0.95, 0.95, -0.10, 0.107, 0)
    box(bm, -0.198, -0.14, -0.95, 0.95, -0.10, 0.10, 0)
    box(bm, -0.198, 0.10, -0.9504, -0.86, -0.06, 0.107, 0)
    box(bm, -0.198, 0.10, 0.86, 0.9504, -0.06, 0.107, 0)
    box(bm, -0.12, 0.12, -0.35, 0.35, 0.065, 0.107, 1)
    obbox(bm, [(-0.16, -0.32, 0.02), (-0.16, 0.32, 0.02), (-0.19, 0.32, 0.09), (-0.19, -0.32, 0.09),
               (-0.19, -0.32, 0.045), (-0.19, 0.32, 0.045), (-0.212, 0.32, 0.107), (-0.212, -0.32, 0.107)], 0)
    for yc in (-0.55, 0.55):
        box(bm, -0.23, -0.15, yc - 0.045, yc + 0.045, -0.025, 0.02, 2)
        box(bm, -0.23, -0.15, yc - 0.045, yc + 0.045, 0.05, 0.095, 2)
        box(bm, -0.15, -0.13, yc - 0.045, yc + 0.045, -0.025, 0.095, 2)
        cyl_y(bm, 0.011, yc - 0.06, yc + 0.06, cx=-0.19, cz=0.0725, seg=12, mi=1)
    for yc in (-0.56, -0.42, 0.42, 0.56):
        cyl_x(bm, 0.032, -0.23, -0.09, cy=yc, cz=-0.045, seg=20, mi=3)
        cyl_x(bm, 0.022, -0.226, -0.150, cy=yc, cz=-0.045, seg=16, mi=1)
        box(bm, -0.11, -0.07, yc - 0.02, yc + 0.02, -0.075, -0.015, 1)
    box(bm, -0.206, -0.196, -0.32, -0.24, 0.0, 0.03, 4)
    box(bm, -0.206, -0.196, 0.24, 0.32, 0.0, 0.03, 4)
    for by, bz in ((0.75, 0.0), (0.75, -0.075), (-0.75, 0.0), (-0.75, -0.075), (0.0, -0.075), (0.65, 0.06), (-0.65, 0.06)):
        cyl_x(bm, 0.009, -0.206, -0.196, cy=by, cz=bz, seg=6, mi=1)
    box(bm, -0.198, 0.05, -0.62, -0.38, 0.107, 0.125, 0)
    box(bm, -0.198, 0.05, 0.38, 0.62, 0.107, 0.125, 0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def grille_bm():
    """Решётка в рамке Body_Front (морда +X, пивот донора):
    X до 0.095, Y +-0.40, Z -0.245..-0.02. Чёрная рамка с вертикальными
    ламелями, красная кузовная плашка сверху, тёмный щиток под надпись."""
    bm = bmesh.new()
    box(bm, 0.05, 0.095, -0.40, 0.40, -0.245, -0.22, 0)
    box(bm, 0.05, 0.095, -0.40, 0.40, -0.045, -0.02, 0)
    box(bm, 0.05, 0.095, -0.40, -0.375, -0.22, -0.045, 0)
    box(bm, 0.05, 0.095, 0.375, 0.40, -0.22, -0.045, 0)
    for i in range(20):
        ys = -0.364 + i * 0.0375
        box(bm, 0.065, 0.095, ys, ys + 0.016, -0.215, -0.05, 0)
    box(bm, 0.05, 0.10, -0.30, 0.30, -0.005, 0.038, 1)
    box(bm, 0.056, 0.062, -0.368, 0.368, -0.212, -0.053, 3)
    for gy, gz in ((-0.387, -0.232), (-0.387, -0.033), (0.387, -0.232), (0.387, -0.033), (0.0, -0.232), (0.0, -0.033)):
        cyl_x(bm, 0.008, 0.093, 0.103, cy=gy, cz=gz, seg=6, mi=3)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm

def platform_bm():
    """Платформа в рамке Body_Top: пол с рифлёным (checker) настилом
    X -1.55..0.10, Y +-0.70, Z 0; обвязка, поперечины, передний щит."""
    bm = bmesh.new()
    x0, x1, y0, y1 = -1.55, 0.10, -0.70, 0.70
    nx, ny = 16, 14
    dx, dy = (x1 - x0) / nx, (y1 - y0) / ny
    grid = [[bm.verts.new((x0 + i * dx, y0 + j * dy, 0.0)) for j in range(ny + 1)] for i in range(nx + 1)]
    cells = []
    for i in range(nx):
        for j in range(ny):
            f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
            f.material_index = 0
            cells.append(f)
    for k, f in enumerate(cells):
        if (k % nx + k // nx) % 2 == 0:
            bmesh.ops.inset_region(bm, faces=[f], thickness=min(dx, dy) * 0.33, depth=0.006, use_even_offset=True)
    box(bm, -1.60, 0.15, -0.75, -0.70, -0.02, 0.04, 0)
    box(bm, -1.60, 0.15, 0.70, 0.75, -0.02, 0.04, 0)
    box(bm, -1.60, -1.50, -0.75, 0.75, -0.02, 0.05, 0)
    box(bm, 0.05, 0.15, -0.75, 0.75, -0.02, 0.30, 1)
    box(bm, 0.03, 0.17, -0.75, 0.75, 0.30, 0.34, 0)
    for xc in (-1.35, -0.85, -0.35, 0.0):
        box(bm, xc - 0.025, xc + 0.025, -0.70, 0.70, -0.08, -0.02, 0)
    for xp in (-1.40, -0.90, -0.40):
        box(bm, xp - 0.03, xp + 0.03, -0.752, -0.692, 0.04, 0.09, 0)
        box(bm, xp - 0.03, xp + 0.03, 0.692, 0.752, 0.04, 0.09, 0)
    for xs in (-1.40, -0.40):
        box(bm, xs - 0.02, xs + 0.02, -0.735, -0.715, 0.09, 0.42, 1)
        box(bm, xs - 0.02, xs + 0.02, 0.715, 0.735, 0.09, 0.42, 1)
    for xd in (-1.30, -0.45):
        for yd in (-0.55, 0.55):
            cyl_z(bm, 0.034, 0.006, 0.021, cx=xd, cy=yd, seg=12, mi=0)
            cyl_z(bm, 0.020, 0.006, 0.024, cx=xd, cy=yd, seg=12, mi=1)
    box(bm, 0.145, 0.155, -0.72, 0.72, 0.10, 0.13, 0)
    box(bm, 0.145, 0.155, -0.72, 0.72, 0.20, 0.23, 0)
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

def build_parts(out):
    m_plast = mat("KAMAZ_PlasticBlack", (0.028, 0.028, 0.032), 0.62)
    m_metal = mat("KAMAZ_MetalDark", (0.075, 0.078, 0.085), 0.42, metal=0.85)
    m_leather = mat("KAMAZ_LeatherBlack", (0.020, 0.020, 0.023), 0.88)
    m_red = mat("KAMAZ_AccentRed", (0.55, 0.05, 0.05), 0.45, metal=0.3)
    m_alu = mat("KAMAZ_AlternAlu", (0.38, 0.39, 0.41), 0.38, metal=0.9)

    rack = obj_from_bm_m(roofrack_bm(), "SM_KAMAZ_Pickup_RoofRack", [m_metal, m_plast, m_red])
    seat_l = obj_from_bm_m(seat_bm(), "SM_KAMAZ_Pickup_Seat_Left", [m_leather, m_red, m_plast])
    seat_r = mirror_object(seat_l, "SM_KAMAZ_Pickup_Seat_Right")
    seat_b = obj_from_bm_m(seat_back_bm(), "SM_KAMAZ_Pickup_Seat_Back", [m_leather, m_red, m_plast])
    alt = obj_from_bm_m(alternator_bm(), "SM_KAMAZ_Pickup_Alternator", [m_alu, m_metal, m_plast])
    bat = obj_from_bm_m(battery_bm(), "SM_KAMAZ_Pickup_Battery", [m_plast, m_metal, m_red])

    parts = (rack, seat_l, seat_r, seat_b, alt, bat)
    for o in parts:
        print(f"[{o.name}] tris={tris(o)}")

    export_one(rack, os.path.join(out, "roofrack_v2.glb"))
    export_one(seat_l, os.path.join(out, "seat_L_v2.glb"))
    export_one(seat_r, os.path.join(out, "seat_R_v2.glb"))
    export_one(seat_b, os.path.join(out, "seat_back_v2.glb"))
    export_one(alt, os.path.join(out, "alternator_v2.glb"))
    export_one(bat, os.path.join(out, "battery_v2.glb"))

    cam, tgt = setup_render()

    def solo(obj, center, views, prefix):
        for p in parts:
            p.hide_render = p is not obj
        render_views(cam, tgt, center, views, out, prefix)

    solo(rack, Vector((0.73, 0.0, 0.80)), {
        "quarter": (Vector((0.7, -0.9, 0.5)), 2.0),
        "side": (Vector((0.15, 1.0, 0.2)), 2.0),
    }, "roofrack_v2")
    solo(seat_l, Vector((-0.10, 0.0, 0.40)), {
        "front": (Vector((0.9, -0.5, 0.35)), 1.1),
        "side": (Vector((0.1, -1.0, 0.2)), 1.1),
    }, "seat_v2")
    solo(seat_b, Vector((-0.06, 0.0, 0.40)), {
        "front": (Vector((1.0, 0.0, 0.15)), 1.9),
        "quarter": (Vector((0.8, -0.5, 0.35)), 1.9),
    }, "seatback_v2")
    solo(alt, Vector((0.08, 0.01, -0.09)), {
        "quarter": (Vector((0.8, -0.6, 0.5)), 0.5),
    }, "alternator_v2")
    solo(bat, Vector((0.0, 0.0, 0.10)), {
        "quarter": (Vector((0.8, -0.6, 0.5)), 0.45),
    }, "battery_v2")
    for p in parts:
        p.hide_render = False

def build_body(out):
    m_plast = mat("KAMAZ_PlasticBlack", (0.028, 0.028, 0.032), 0.62)
    m_metal = mat("KAMAZ_MetalDark", (0.075, 0.078, 0.085), 0.42, metal=0.85)
    m_bodyred = mat("KAMAZ_BodyRed", (0.784, 0.122, 0.180), 0.35)
    m_white = mat("KAMAZ_LensWhite", (0.95, 0.96, 1.00), 0.20)
    m_warm = mat("KAMAZ_LensWarm", (1.00, 0.72, 0.40), 0.25)
    m_alu = mat("KAMAZ_AlternAlu", (0.38, 0.39, 0.41), 0.38, metal=0.9)

    bfront = obj_from_bm_m(bumper_front_bm(), "SK_KAMAZ_Pickup_Bumper_Front", [m_plast, m_metal, m_bodyred, m_white, m_warm])
    bback = obj_from_bm_m(bumper_back_bm(), "SK_KAMAZ_Pickup_Bumper_Back", [m_plast, m_metal, m_bodyred, m_alu, m_white])
    grille = obj_from_bm_m(grille_bm(), "SK_KAMAZ_Pickup_Grille", [m_plast, m_bodyred, m_white, m_metal])
    add_text(grille, "KAMAZ", 0.024, (0.100, 0.0, 0.0165), (radians(90), 0.0, radians(90)), m_white)
    platform = obj_from_bm_m(platform_bm(), "SK_KAMAZ_Pickup_Platform", [m_metal, m_plast])

    parts = (bfront, bback, grille, platform)
    for o in parts:
        print(f"[{o.name}] tris={tris(o)}")

    export_one(bfront, os.path.join(out, "bumper_front_v2.glb"))
    export_one(bback, os.path.join(out, "bumper_back_v2.glb"))
    export_one(grille, os.path.join(out, "grille_v2.glb"))
    export_one(platform, os.path.join(out, "platform_v2.glb"))

    cam, tgt = setup_render()

    def solo(obj, center, views, prefix):
        for p in parts:
            p.hide_render = p is not obj
        render_views(cam, tgt, center, views, out, prefix)

    solo(bfront, Vector((0.0, 0.0, 0.15)), {
        "front": (Vector((1.0, 0.0, 0.08)), 2.3),
        "quarter": (Vector((0.85, -0.5, 0.35)), 2.3),
    }, "bumper_front_v2")
    solo(bback, Vector((-0.02, 0.0, 0.0)), {
        "rear": (Vector((-1.0, 0.0, 0.08)), 2.2),
        "quarter": (Vector((-0.85, -0.5, 0.35)), 2.2),
    }, "bumper_back_v2")
    solo(grille, Vector((0.07, 0.0, -0.10)), {
        "front": (Vector((1.0, 0.0, 0.1)), 1.0),
        "quarter": (Vector((0.85, -0.45, 0.3)), 1.0),
    }, "grille_v2")
    solo(platform, Vector((-0.72, 0.0, 0.12)), {
        "quarter": (Vector((0.8, -0.6, 0.55)), 2.3),
        "top": (Vector((0.2, 0.0, 1.0)), 2.3),
    }, "platform_v2")
    for p in parts:
        p.hide_render = False

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
    if stage in ("parts", "all"):
        build_parts(out)
    if stage in ("body", "all"):
        build_body(out)
    print("DONE")

main()
