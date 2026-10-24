
# KAMAZ off-road pickup blockout for SCUM
# Blender 3.6+ / 4.x. Run via Scripting > Run Script.
# Units: meters. Front of vehicle is -Y, rear is +Y, Z is up.
import bpy, math
from mathutils import Vector, Euler

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
    for block in list(datablocks):
        if block.users == 0:
            datablocks.remove(block)

# Materials
def mat(name, color, metallic=0.0, roughness=0.45):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    return m

BODY = mat('Paint | Urban Camo Light', (0.62, 0.64, 0.66), 0.12, 0.42)
RED = mat('Accent | Tow Hook Red', (0.72, 0.018, 0.028), 0.42, 0.25)
BLACK = mat('Trim | Graphite Black', (0.025, 0.032, 0.042), 0.22, 0.34)
RUBBER = mat('Rubber', (0.012, 0.014, 0.016), 0.0, 0.82)
GLASS = mat('Glass | Dark Tinted', (0.018, 0.055, 0.075), 0.18, 0.16)
METAL = mat('Metal | Gunmetal', (0.16, 0.18, 0.20), 0.72, 0.3)
WHITE = mat('LED | Cool White', (0.8, 0.92, 1.0), 0.15, 0.18)
DARK = mat('Grille Recess', (0.006, 0.008, 0.01), 0.05, 0.5)
DRL = mat('LED | Ice Blue', (0.55, 0.75, 1.0), 0.15, 0.2)

# Collections for a tidy hierarchy
root = bpy.context.scene.collection

def move_to_collection(obj, collection_name):
    col = bpy.data.collections.get(collection_name)
    if col is None:
        col = bpy.data.collections.new(collection_name)
        root.children.link(col)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj

def cube(name, loc, scale, material, bevel=0.04):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material: o.data.materials.append(material)
    if bevel:
        mod = o.modifiers.new('Soft manufactured edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        o.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    return o

def cyl(name, loc, radius, depth, material, vertices=24, rot=(math.pi/2,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    if material: o.data.materials.append(material)
    bevel = o.modifiers.new('Edge bevel', 'BEVEL'); bevel.width = 0.025; bevel.segments = 2
    o.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    return o

def text_obj(name, body, loc, size, material, rot=(math.pi/2,0,0), extrude=0.002):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    ob = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(ob)
    ob.location = loc; ob.rotation_euler = rot
    if material: cu.materials.append(material)
    return ob

# Chassis / underbody
cube('Chassis | ladder frame', (0, 0.1, 0.62), (1.42, 4.60, 0.18), BLACK, 0.06)
cube('Underbody skid plate', (0, -1.90, 0.52), (1.40, 0.90, 0.10), METAL, 0.04)

# Main body panels (Ranger Raptor-style proportions: long hood, double cab, long bed)
cube('Lower body shell', (0, 0.15, 1.00), (1.84, 4.90, 0.64), BODY, 0.12)
cube('Hood', (0, -1.62, 1.42), (1.80, 1.30, 0.16), BODY, 0.10)
cube('Hood scoop', (0, -1.95, 1.53), (0.62, 0.50, 0.10), BLACK, 0.04)

# Double cab greenhouse: raked windshield, four door windows, quarter glass, rear glass
cube('Cab shell', (0, 0.05, 1.71), (1.78, 2.00, 0.54), BODY, 0.11)
windshield = cube('Windshield dark glass', (0, -0.66, 1.70), (1.50, 0.035, 0.70), GLASS, 0.025)
windshield.rotation_euler[0] = math.radians(-28)
cube('Rear cab window', (0, 1.05, 1.72), (1.42, 0.035, 0.50), GLASS, 0.02)
for side in (-1, 1):
    x = side * 0.90
    cube(f'Front side window {side}', (x, -0.40, 1.72), (0.035, 0.64, 0.42), GLASS, 0.025)
    cube(f'Rear side window {side}', (x, 0.35, 1.72), (0.035, 0.66, 0.42), GLASS, 0.025)
    cube(f'Quarter window {side}', (x, 0.86, 1.72), (0.035, 0.26, 0.36), GLASS, 0.02)
    # door seam accents and handles
    for y in (-0.35, 0.45):
        cube(f'Door handle {side} {y}', (side*0.935, y, 1.24), (0.025, 0.18, 0.045), BLACK, 0.012)
    cube(f'Side mirror arm {side}', (side*0.97, -0.88, 1.52), (0.16, 0.07, 0.05), BLACK, 0.02)
    cube(f'Side mirror housing {side}', (side*1.10, -0.88, 1.56), (0.20, 0.14, 0.26), BLACK, 0.04)
    # side steps
    cube(f'Running board {side}', (side*1.00, 0.05, 0.62), (0.18, 1.60, 0.10), BLACK, 0.035)
    cube(f'Step metal insert {side}', (side*1.01, 0.05, 0.678), (0.12, 1.40, 0.016), METAL, 0.008)

# Pickup bed: body-color walls, black tonneau cover, tailgate lettering
cube('Bed floor', (0, 1.80, 1.24), (1.56, 1.42, 0.06), BLACK, 0.035)
for side in (-1,1):
    cube(f'Bed side wall {side}', (side*0.82, 1.80, 1.34), (0.14, 1.50, 0.26), BODY, 0.05)
cube('Bed tonneau cover', (0, 1.80, 1.48), (1.66, 1.50, 0.06), BLACK, 0.025)
cube('Tailgate', (0, 2.58, 1.28), (1.50, 0.12, 0.42), BODY, 0.06)
text_obj('Tailgate KAMAZ lettering', 'KAMAZ', (0, 2.647, 1.31), 0.20, BLACK, rot=(math.pi/2, 0, math.pi), extrude=0.001)

# Grille, lettering and headlights on the -Y face
cube('Main grille recess', (0, -2.32, 1.26), (1.24, 0.06, 0.44), DARK, 0.025)
for z in (1.12, 1.22, 1.32, 1.42):
    cube(f'Grille horizontal slat {z}', (0, -2.348, z), (1.16, 0.035, 0.055), BLACK, 0.012)
text_obj('Front KAMAZ lettering', 'KAMAZ', (0, -2.392, 1.50), 0.17, WHITE, rot=(math.pi/2,0,0), extrude=0.002)
# Angular LED headlamps with ice-blue DRL strips, fog lamps in the bumper
for side in (-1,1):
    cube(f'Headlamp housing {side}', (side*0.72, -2.34, 1.52), (0.38, 0.10, 0.26), BLACK, 0.035)
    cube(f'Headlamp LED main {side}', (side*0.72, -2.394, 1.56), (0.30, 0.018, 0.07), WHITE, 0.012)
    cube(f'Headlamp DRL strip {side}', (side*0.72, -2.396, 1.45), (0.32, 0.018, 0.035), DRL, 0.012)
    cube(f'Fog lamp housing {side}', (side*0.74, -2.55, 0.78), (0.30, 0.14, 0.16), BLACK, 0.025)
    cube(f'Fog LED {side}', (side*0.74, -2.625, 0.78), (0.20, 0.018, 0.09), DRL, 0.012)

# Front and rear armored bumpers with skid plates
cube('Front armored bumper', (0, -2.44, 0.78), (2.06, 0.34, 0.42), BLACK, 0.07)
cube('Front bumper center skid', (0, -2.57, 0.55), (0.80, 0.10, 0.22), METAL, 0.035)
cube('Rear armored bumper', (0, 2.64, 0.74), (2.00, 0.26, 0.36), BLACK, 0.06)
cube('Rear bumper skid', (0, 2.72, 0.50), (0.70, 0.08, 0.14), METAL, 0.035)
# Red tow shackles in both bumpers
for y, label in ((-2.66,'Front'), (2.81,'Rear')):
    for side in (-1,1):
        x = side*0.63
        cube(f'{label} tow shackle stem {side}', (x, y, 0.84), (0.07, 0.07, 0.16), RED, 0.025)
        cube(f'{label} tow shackle base {side}', (x, y, 0.76), (0.20, 0.07, 0.055), RED, 0.025)

# Wheels: lifted stance, chunky mud-terrain tires, gunmetal rims, red hub caps
wheel_y = (-1.80, 1.35)
wheel_z = 0.47
for axle, y in enumerate(wheel_y):
    for side in (-1,1):
        x = side*0.98
        # Cylinder axis is X (rotated 90 degrees around Y)
        tire = cyl(f'Tire | axle {axle+1} | side {side}', (x, y, wheel_z), 0.45, 0.34, RUBBER, vertices=32, rot=(0, math.pi/2, 0))
        rim = cyl(f'Wheel rim | axle {axle+1} | side {side}', (x + side*0.155, y, wheel_z), 0.29, 0.04, METAL, vertices=24, rot=(0, math.pi/2, 0))
        ring = cyl(f'Rim lip | axle {axle+1} | side {side}', (x + side*0.175, y, wheel_z), 0.305, 0.02, BLACK, vertices=24, rot=(0, math.pi/2, 0))
        hub = cyl(f'Hub | axle {axle+1} | side {side}', (x + side*0.178, y, wheel_z), 0.10, 0.05, DARK, vertices=16, rot=(0, math.pi/2, 0))
        cap = cyl(f'Hub cap | axle {axle+1} | side {side}', (x + side*0.203, y, wheel_z), 0.035, 0.02, RED, vertices=12, rot=(0, math.pi/2, 0))
        # Tread lugs arranged around the tire circumference; deliberately low-detail for game blockout
        for j in range(14):
            a = 2*math.pi*j/14
            yy = y + 0.44*math.sin(a)
            zz = wheel_z + 0.44*math.cos(a)
            lug = cube(f'Tread lug {axle}-{side}-{j}', (x, yy, zz), (0.36, 0.15, 0.07), RUBBER, 0.018)
            lug.rotation_euler[0] = a * 0.55
        # Fender flares: broad black arches over each wheel
        cube(f'Fender flare top {axle}-{side}', (side*1.02, y, 1.26), (0.26, 1.10, 0.12), BLACK, 0.045)
        cube(f'Fender flare front cheek {axle}-{side}', (side*1.02, y-0.48, 1.06), (0.24, 0.14, 0.34), BLACK, 0.035)
        cube(f'Fender flare rear cheek {axle}-{side}', (side*1.02, y+0.48, 1.06), (0.24, 0.14, 0.34), BLACK, 0.035)

# Roof rails and antenna
for side in (-1,1):
    cube(f'Roof rail {side}', (side*0.80, 0.32, 2.01), (0.06, 1.30, 0.05), BLACK, 0.02)
cyl('Roof antenna', (-0.58, -0.55, 2.05), 0.012, 0.18, BLACK, vertices=8, rot=(0,0,0))
# Sports bar behind the cab (black, just below the roof line)
for side in (-1,1):
    cube(f'Roll bar upright {side}', (side*0.62, 1.12, 1.70), (0.09, 0.10, 0.55), BLACK, 0.04)
cube('Roll bar cross member', (0, 1.12, 1.94), (1.35, 0.10, 0.09), BLACK, 0.05)

# Rear lamps on the tailgate face
for side in (-1,1):
    cube(f'Tail lamp housing {side}', (side*0.60, 2.655, 1.28), (0.16, 0.05, 0.36), BLACK, 0.025)
    cube(f'Tail lamp red strip {side}', (side*0.60, 2.682, 1.30), (0.105, 0.018, 0.25), RED, 0.018)

# Camera-friendly floor and lighting, so the scene opens ready to inspect
floor_mat = mat('Studio floor', (0.055, 0.065, 0.078), 0.15, 0.62)
cube('Ground', (0, 0, -0.02), (200, 200, 0.1), floor_mat, 0)

# Organize generated vehicle parts into collections by rough naming group
for obj in list(bpy.context.scene.objects):
    if obj.name == 'Ground':
        move_to_collection(obj, '00 | Studio')
    elif any(k in obj.name.lower() for k in ('tire','rim','hub','tread lug','fender flare')):
        move_to_collection(obj, '04 | Wheels and Flares')
    elif any(k in obj.name.lower() for k in ('grille','headlamp','fog','bumper','tow shackle','kamaz lettering')):
        move_to_collection(obj, '03 | Front and Rear Details')
    elif any(k in obj.name.lower() for k in ('bed','tailgate','roll bar','tail lamp')):
        move_to_collection(obj, '02 | Pickup Bed')
    else:
        move_to_collection(obj, '01 | Body and Cab')

# Set scene units and a useful viewport angle
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
_valid_engines = {item.identifier for item in scene.render.bl_rna.properties['engine'].enum_items}
scene.render.engine = ('BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in _valid_engines
                       else 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in _valid_engines else 'CYCLES')
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        area.spaces.active.region_3d.view_distance = 8.5
        area.spaces.active.region_3d.view_location = (0, 0, 1.1)
        area.spaces.active.region_3d.view_rotation = Euler(
            (math.radians(65), 0.0, math.radians(-25)), 'XYZ').to_quaternion()

# Select body root-ish object and leave a clear scene state
bpy.ops.object.select_all(action='DESELECT')
obj = bpy.data.objects.get('Lower body shell')
if obj:
    obj.select_set(True); bpy.context.view_layer.objects.active = obj

# ---------------------------------------------------------------------------
# Game export (works headless too):
#   blender --background --python kamaz_scum_blockout.py -- <out_dir>
# Produces KAMAZ_Pickup_Blockout.fbx (LOD0+LOD1+LOD2+UCX), .glb and previews.
# ---------------------------------------------------------------------------
import os, sys

def cli_out_dir():
    argv = sys.argv
    if '--' in argv:
        rest = argv[argv.index('--') + 1:]
        if rest:
            return rest[0]
    return None

def add_uv_smart(obj, margin=0.02):
    if obj.type != 'MESH' or obj.data.uv_layers:
        return
    obj.data.uv_layers.new(name='UVMap')
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')

out_dir = cli_out_dir()
if out_dir:
    os.makedirs(out_dir, exist_ok=True)

    # Text lettering must become real geometry to survive export
    for ob in [o for o in bpy.context.scene.objects if o.type == 'FONT']:
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.convert(target='MESH')

    # UV unwrap every vehicle part (studio floor is excluded everywhere below)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in bpy.context.scene.objects:
        if ob.type == 'MESH' and ob.name != 'Ground':
            add_uv_smart(ob)

    # Simple convex collision hulls (UE UCX_ prefix), positioned from known dims
    ucx = [
        cube('UCX_KAMAZ_Pickup_Blockout_01', (0, 0.15, 1.00), (1.92, 5.20, 0.72), None, 0),
        cube('UCX_KAMAZ_Pickup_Blockout_02', (0, 0.05, 1.70), (1.84, 2.10, 0.68), None, 0),
        cube('UCX_KAMAZ_Pickup_Blockout_03', (0, 1.80, 1.30), (1.72, 1.60, 0.55), None, 0),
    ]
    for u in ucx:
        u.hide_render = True

    # Join everything (minus floor) into the LOD0 game mesh
    bpy.ops.object.select_all(action='DESELECT')
    parts = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name != 'Ground' and not o.name.startswith('UCX_')]
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    game = bpy.context.object
    game.name = 'KAMAZ_Pickup_Blockout'

    # LODs as decimated copies; UE FBX import picks them up via _LOD<n> suffix
    for i, ratio in enumerate((0.5, 0.25), start=1):
        dup = game.copy()
        dup.data = game.data.copy()
        bpy.context.collection.objects.link(dup)
        dup.name = 'KAMAZ_Pickup_Blockout_LOD%d' % i
        bpy.context.view_layer.objects.active = dup
        bpy.ops.object.select_all(action='DESELECT')
        dup.select_set(True)
        dec = dup.modifiers.new('Decimate', 'DECIMATE')
        dec.ratio = ratio
        bpy.ops.object.modifier_apply(modifier=dec.name)
        dup.hide_render = True

    # FBX with LOD0 + LODs + UCX collision
    bpy.ops.object.select_all(action='DESELECT')
    for name in ('KAMAZ_Pickup_Blockout', 'KAMAZ_Pickup_Blockout_LOD1', 'KAMAZ_Pickup_Blockout_LOD2') :
        o = bpy.data.objects.get(name)
        if o:
            o.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(out_dir, 'KAMAZ_Pickup_Blockout.fbx'),
        use_selection=True, mesh_smooth_type='FACE', add_leaf_bones=False,
        bake_space_transform=True, path_mode='COPY')

    # glTF preview mesh
    bpy.ops.object.select_all(action='DESELECT')
    game.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out_dir, 'KAMAZ_Pickup_Blockout.glb'), use_selection=True)

    # Preview renders: camera + sun, three angles
    cam_data = bpy.data.cameras.new('PreviewCam')
    cam_data.lens = 40
    cam = bpy.data.objects.new('PreviewCam', cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    sun_data = bpy.data.lights.new('PreviewSun', 'SUN')
    sun_data.energy = 2.0
    sun = bpy.data.objects.new('PreviewSun', sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    if scene.world is None:
        scene.world = bpy.data.worlds.new('World')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (0.35, 0.35, 0.40, 1.0)

    shots = {
        'preview_front34.png': (7.2, -6.0, 1.9),
        'preview_side.png': (9.6, 0.1, 1.7),
        'preview_rear34.png': (-6.6, 7.4, 2.6),
    }
    for fname, loc in shots.items():
        cam.location = loc
        # aim at truck center
        direction = Vector((0, 0, 1.1)) - Vector(loc)
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = os.path.join(out_dir, fname)
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError:
            scene.render.engine = 'CYCLES'
            scene.cycles.samples = 32
            scene.cycles.device = 'CPU'
            bpy.ops.render.render(write_still=True)

    tris = sum(len(p.vertices) - 2 for p in game.data.polygons)
    stats = ('mesh: %s\nverts: %d\ntris(LOD0): %d\nLOD1 ratio: 0.5\nLOD2 ratio: 0.25\n'
             'collision: 3x UCX box\nUV: smart_project 66deg\n' % (game.name, len(game.data.vertices), tris))
    with open(os.path.join(out_dir, 'stats.txt'), 'w') as f:
        f.write(stats)
    print(stats)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, 'kamaz_blockout.blend'))

print('KAMAZ SCUM pickup blockout created. Save as .blend and refine proportions/materials before game export.')
