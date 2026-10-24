import unreal

TASK = unreal.AssetImportTask()
TASK.filename = 'D:/SteamLibrary/KAMAZ_UE/Import/KAMAZ_Pickup_Blockout.fbx'
TASK.destination_path = '/Game/ConZ_Files/Models/Vehicles2/Pickup/Meshes'
TASK.destination_name = 'SM_KAMAZ_Pickup_Wheel_FrontLeft'
TASK.automated = True
TASK.save = True
TASK.replace_existing = True

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
TASK.options = opts

unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([TASK])

path = '/Game/ConZ_Files/Models/Vehicles2/Pickup/Meshes/SM_KAMAZ_Pickup_Wheel_FrontLeft'
if unreal.EditorAssetLibrary.does_asset_exist(path):
    m = unreal.load_asset(path)
    bb = m.get_bounding_box()
    ext = bb.get_extent()
    sz = bb.get_size()
    mats = m.static_materials
    slot0 = mats[0].material_slot_name if len(mats) else 'none'
    unreal.log('KAMAZ_IMPORT_OK size=(%.1f, %.1f, %.1f)cm slots=%d slot0=%s' % (sz.x, sz.y, sz.z, len(mats), slot0))
else:
    unreal.log('KAMAZ_IMPORT_FAIL')
