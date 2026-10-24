import unreal

FBX_DIR = 'D:/SteamLibrary/KAMAZ_UE/Import/detail_v2'
DEST = '/Game/ConZ_Files/Models/Vehicles2/Pickup/Meshes'

JOBS = [
    ('SM_KAMAZ_Pickup_Wheel_FrontLeft.fbx', 'SM_KAMAZ_Pickup_Wheel_FrontLeft'),
    ('SM_KAMAZ_Pickup_Wheel_FrontLeft.fbx', 'SM_KAMAZ_Pickup_Wheel_FrontRight'),
    ('SM_KAMAZ_Pickup_Wheel_FrontLeft.fbx', 'SM_KAMAZ_Pickup_Wheel_BackLeft'),
    ('SM_KAMAZ_Pickup_Wheel_FrontLeft.fbx', 'SM_KAMAZ_Pickup_Wheel_BackRight'),
    ('SM_KAMAZ_Pickup_Light_Top.fbx', 'SM_KAMAZ_Pickup_Light_Top'),
    ('SM_KAMAZ_Pickup_Lights_FrontLeft.fbx', 'SM_KAMAZ_Pickup_Lights_FrontLeft'),
    ('SM_KAMAZ_Pickup_Lights_FrontRight.fbx', 'SM_KAMAZ_Pickup_Lights_FrontRight'),
    ('SM_KAMAZ_Pickup_Light_BackLeft.fbx', 'SM_KAMAZ_Pickup_Light_BackLeft'),
    ('SM_KAMAZ_Pickup_Light_BackRight.fbx', 'SM_KAMAZ_Pickup_Light_BackRight'),
    ('SM_KAMAZ_Pickup_RoofRack.fbx', 'SM_KAMAZ_Pickup_RoofRack'),
    ('SM_KAMAZ_Pickup_Seat_Left.fbx', 'SM_KAMAZ_Pickup_Seat_Left'),
    ('SM_KAMAZ_Pickup_Seat_Right.fbx', 'SM_KAMAZ_Pickup_Seat_Right'),
    ('SM_KAMAZ_Pickup_Seat_Back.fbx', 'SM_KAMAZ_Pickup_Seat_Back'),
    ('SM_KAMAZ_Pickup_Alternator.fbx', 'SM_KAMAZ_Pickup_Alternator'),
    ('SM_KAMAZ_Pickup_Battery.fbx', 'SM_KAMAZ_Pickup_Battery'),
]

opts = unreal.FbxImportUI()
opts.import_mesh = True
opts.import_textures = False
opts.import_materials = False
opts.import_as_skeletal = False
opts.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
sm = unreal.FbxStaticMeshImportData()
sm.combine_meshes = True
sm.auto_generate_collision = False
sm.import_translation = unreal.Vector(0.0, 0.0, 0.0)
opts.static_mesh_import_data = sm

tasks = []
for fname, dname in JOBS:
    t = unreal.AssetImportTask()
    t.filename = FBX_DIR + '/' + fname
    t.destination_path = DEST
    t.destination_name = dname
    t.automated = True
    t.save = True
    t.replace_existing = True
    t.options = opts
    tasks.append(t)

unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

fails = 0
for _, dname in JOBS:
    p = DEST + '/' + dname
    try:
        m = unreal.load_asset(p)
        sz = m.get_bounding_box().get_size()
        n = len(m.static_materials)
        unreal.log('KAMAZ_IMPORT_OK %s size=(%.1f,%.1f,%.1f) slots=%d' % (dname, sz.x, sz.y, sz.z, n))
    except Exception:
        fails += 1
        unreal.log('KAMAZ_IMPORT_FAIL %s' % dname)
unreal.log('KAMAZ_IMPORT_DONE fails=%d' % fails)
