
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

RED = mat('Paint | KAMAZ Red', (0.72, 0.018, 0.028), 0.42, 0.25)
BLACK = mat('Trim | Graphite Black', (0.025, 0.032, 0.042), 0.22, 0.34)
RUBBER = mat('Rubber', (0.012, 0.014, 0.016), 0.0, 0.82)
GLASS = mat('Glass | Dark Tinted', (0.018, 0.055, 0.075), 0.18, 0.16)
METAL = mat('Metal | Gunmetal', (0.16, 0.18, 0.20), 0.72, 0.3)
WHITE = mat('LED | Cool White', (0.8, 0.92, 1.0), 0.15, 0.18)
DARK = mat('Grille Recess', (0.006, 0.008, 0.01), 0.05, 0.5)

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
cube('Chassis | ladder frame', (0, 0.05, 0.82), (1.48, 3.95, 0.22), BLACK, 0.06)
cube('Underbody skid plate', (0, -1.05, 0.68), (1.5, 0.8, 0.12), METAL, 0.04)

# Main body panels
cube('Lower body shell', (0, 0.0, 1.18), (1.82, 4.25, 0.58), RED, 0.12)
cube('Hood', (0, -1.38, 1.66), (1.88, 1.25, 0.22), RED, 0.10)
cube('Front fascia', (0, -2.06, 1.40), (1.72, 0.16, 0.58), BLACK, 0.05)

# Double cab: cabin body, windshield and rear glass
cube('Cab shell', (0, -0.42, 2.02), (1.78, 1.82, 1.18), RED, 0.11)
cube('Windshield dark glass', (0, -1.355, 2.22), (1.52, 0.035, 0.66), GLASS, 0.025)
cube('Rear cab window', (0, 0.505, 2.22), (1.43, 0.035, 0.62), GLASS, 0.02)
# Side windows on both sides, front and rear door windows
for side in (-1, 1):
    x = side * 0.905
    cube(f'Front side window {side}', (x, -0.77, 2.24), (0.035, 0.72, 0.56), GLASS, 0.025)
    cube(f'Rear side window {side}', (x, -0.02, 2.24), (0.035, 0.57, 0.56), GLASS, 0.025)
    # door seam accents and handles
    for y in (-0.72, -0.03):
        cube(f'Door handle {side} {y}', (side*0.928, y, 1.78), (0.025, 0.18, 0.045), BLACK, 0.012)
    cube(f'Side mirror arm {side}', (side*1.04, -1.10, 2.05), (0.23, 0.08, 0.06), BLACK, 0.02)
    cube(f'Side mirror housing {side}', (side*1.17, -1.10, 2.10), (0.22, 0.28, 0.20), BLACK, 0.04)
    # side steps
    cube(f'Running board {side}', (side*0.99, -0.05, 0.88), (0.20, 1.35, 0.12), BLACK, 0.035)
    cube(f'Step metal insert {side}', (side*1.00, -0.05, 0.948), (0.14, 1.12, 0.018), METAL, 0.008)

# Pickup bed, rails and tailgate
cube('Bed floor', (0, 1.40, 1.35), (1.62, 1.48, 0.12), BLACK, 0.035)
for side in (-1,1):
    cube(f'Bed side wall {side}', (side*0.82, 1.40, 1.60), (0.12, 1.55, 0.48), RED, 0.05)
    cube(f'Bed top rail {side}', (side*0.82, 1.40, 1.86), (0.15, 1.62, 0.08), BLACK, 0.025)
# Tailgate rear face
cube('Tailgate', (0, 2.20, 1.57), (1.55, 0.12, 0.50), RED, 0.06)
text_obj('Tailgate KAMAZ lettering', 'KAMAZ', (0, 2.267, 1.61), 0.24, BLACK, rot=(math.pi/2,0,0), extrude=0.001)

# Grille and brand lettering on front (front face is -Y)
cube('Main grille recess', (0, -2.155, 1.43), (1.18, 0.045, 0.42), DARK, 0.025)
for z in (1.28, 1.35, 1.42, 1.49, 1.56):
    cube(f'Grille horizontal slat {z}', (0, -2.184, z), (1.10, 0.035, 0.025), METAL, 0.008)
text_obj('Front KAMAZ lettering', 'KAMAZ', (0, -2.215, 1.52), 0.24, WHITE, rot=(math.pi/2,0,0), extrude=0.002)
# Headlights and lower fog lamps
for side in (-1,1):
    cube(f'Headlamp housing {side}', (side*0.70, -2.16, 1.62), (0.34, 0.08, 0.32), BLACK, 0.035)
    cube(f'Headlamp LED upper {side}', (side*0.70, -2.208, 1.69), (0.24, 0.018, 0.055), WHITE, 0.012)
    cube(f'Headlamp LED lower {side}', (side*0.70, -2.208, 1.57), (0.24, 0.018, 0.055), WHITE, 0.012)
    cube(f'Fog lamp housing {side}', (side*0.70, -2.12, 1.10), (0.38, 0.12, 0.18), BLACK, 0.025)
    for i in range(3):
        cyl(f'Fog LED {side} {i}', (side*0.70 + (i-1)*0.095, -2.195, 1.10), 0.035, 0.018, WHITE, vertices=12, rot=(math.pi/2,0,0))

# Front and rear armored bumpers
cube('Front armored bumper', (0, -2.22, 1.03), (2.02, 0.30, 0.34), BLACK, 0.07)
cube('Front bumper center skid', (0, -2.395, 0.89), (0.78, 0.08, 0.18), METAL, 0.035)
cube('Rear armored bumper', (0, 2.28, 1.02), (1.98, 0.28, 0.30), BLACK, 0.06)
# Tow shackles (stylized as red bars + bottom bar)
for y, label in ((-2.43,'Front'), (2.45,'Rear')):
    for side in (-1,1):
        x = side*0.63
        cube(f'{label} tow shackle stem {side}', (x, y, 0.91), (0.07, 0.07, 0.16), RED, 0.025)
        cube(f'{label} tow shackle base {side}', (x, y, 0.83), (0.20, 0.07, 0.055), RED, 0.025)

# Wheels: four chunky tires, rims, red rings and simplified tread blocks
wheel_y = (-1.35, 1.42)
wheel_z = 0.78
for axle, y in enumerate(wheel_y):
    for side in (-1,1):
        x = side*1.02
        # Cylinder axis is X (rotated 90 degrees around Y)
        tire = cyl(f'Tire | axle {axle+1} | side {side}', (x, y, wheel_z), 0.58, 0.34, RUBBER, vertices=32, rot=(0, math.pi/2, 0))
        rim = cyl(f'Wheel rim | axle {axle+1} | side {side}', (x + side*0.18, y, wheel_z), 0.34, 0.035, BLACK, vertices=24, rot=(0, math.pi/2, 0))
        ring = cyl(f'Red rim ring | axle {axle+1} | side {side}', (x + side*0.202, y, wheel_z), 0.285, 0.025, RED, vertices=24, rot=(0, math.pi/2, 0))
        hub = cyl(f'Hub | axle {axle+1} | side {side}', (x + side*0.225, y, wheel_z), 0.105, 0.04, METAL, vertices=16, rot=(0, math.pi/2, 0))
        # Tread lugs arranged around the tire circumference; deliberately low-detail for game blockout
        for j in range(16):
            a = 2*math.pi*j/16
            yy = y + 0.565*math.sin(a)
            zz = wheel_z + 0.565*math.cos(a)
            lug = cube(f'Tread lug {axle}-{side}-{j}', (x, yy, zz), (0.36, 0.16, 0.075), RUBBER, 0.018)
            lug.rotation_euler[0] = a * 0.55
        # Fender flares: broad simplified arches represented by upper and side armor pieces
        cube(f'Fender flare top {axle}-{side}', (side*1.02, y, 1.48), (0.24, 1.30, 0.14), BLACK, 0.045)
        cube(f'Fender flare front cheek {axle}-{side}', (side*1.02, y-0.57, 1.30), (0.23, 0.16, 0.38), BLACK, 0.035)
        cube(f'Fender flare rear cheek {axle}-{side}', (side*1.02, y+0.57, 1.30), (0.23, 0.16, 0.38), BLACK, 0.035)

# Roof rack / light bar
cube('Roof light bar support', (0, -0.35, 2.66), (1.30, 0.10, 0.07), BLACK, 0.025)
for i in range(5):
    x = (i-2)*0.27
    cube(f'Roof LED {i}', (x, -0.40, 2.72), (0.18, 0.07, 0.07), WHITE, 0.018)
# Rear sports bar / bed roll bar
for side in (-1,1):
    cube(f'Roll bar upright {side}', (side*0.70, 0.73, 2.02), (0.10, 0.12, 0.92), BLACK, 0.04)
cube('Roll bar cross member', (0, 0.73, 2.45), (1.45, 0.12, 0.12), BLACK, 0.05)

# Rear lamps
for side in (-1,1):
    cube(f'Tail lamp housing {side}', (side*0.79, 2.275, 1.57), (0.18, 0.05, 0.42), BLACK, 0.025)
    cube(f'Tail lamp red strip {side}', (side*0.79, 2.307, 1.61), (0.105, 0.018, 0.25), RED, 0.018)

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
scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(scene, 'eevee') else 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        area.spaces.active.region_3d.view_distance = 8.5
        area.spaces.active.region_3d.view_location = (0, 0, 1.1)
        area.spaces.active.region_3d.view_rotation = (math.radians(65), 0, math.radians(-25))

# Select body root-ish object and leave a clear scene state
bpy.ops.object.select_all(action='DESELECT')
obj = bpy.data.objects.get('Lower body shell')
if obj:
    obj.select_set(True); bpy.context.view_layer.objects.active = obj

print('KAMAZ SCUM pickup blockout created. Save as .blend and refine proportions/materials before game export.')
