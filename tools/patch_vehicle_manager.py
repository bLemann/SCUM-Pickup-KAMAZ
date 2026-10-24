import struct, sys

SRC = r'C:\Users\leman\AppData\Local\Temp\rufp\registry_check\stock_vm\SCUM\Content\ConZ_Files\Vehicles'
OUT = r'D:\SteamLibrary\KAMAZ_UE\modpack\SCUM\Content\ConZ_Files\Vehicles'

ua = open(SRC + r'\BP_VehicleManager.uasset', 'rb').read()
ue = open(SRC + r'\BP_VehicleManager.uexp', 'rb').read()

# ---------- parse ----------
def i32(d, o): return struct.unpack_from('<i', d, o)[0]
def u32(d, o): return struct.unpack_from('<I', d, o)[0]

NC, NOFF = i32(ua, 41), i32(ua, 45)
EC, EOFF = i32(ua, 57), i32(ua, 61)
IC, IOFF = i32(ua, 65), i32(ua, 69)
DEP, ARD, BULK = i32(ua, 73), i32(ua, 165), struct.unpack_from('<q', ua, 169)[0]
PCNT, POFF = i32(ua, 185), i32(ua, 189)
assert (NC, NOFF, EC, EOFF, IC, IOFF) == (215, 193, 5, 14096, 108, 11072), 'summary mismatch'

names = []
o = NOFF
for _ in range(NC):
    l = i32(ua, o); o += 4
    names.append(ua[o:o+l-1].decode('latin1')); o += l + 4

imports = []
o = IOFF
for _ in range(IC):
    imports.append(struct.unpack_from('<7i', ua, o)); o += 28

exports = []
o = EOFF
for _ in range(EC):
    e = list(struct.unpack_from('<26i', ua, o))
    exports.append(e); o += 104
assert o == DEP == 14616

# ---------- new content ----------
VEH_K = '/Game/ConZ_Files/Vehicles/Car/Rager/BPC_KAMAZ_Pickup.BPC_KAMAZ_Pickup_C'
VEH_L = '/Game/ConZ_Files/Vehicles/Car/Laika/BPC_KAMAZ_Pickup_Laika.BPC_KAMAZ_Pickup_Laika_C'
PDIR = '/Game/ConZ_Files/Vehicles/SpawningPresets/ManualSpawn/'
KPRE = ['KAMAZ_PickupManualSpawnPreset', 'KAMAZ_PickupManualSpawnPreset_Full',
        'KAMAZ_PickupManualSpawnPreset_MinimalFunctional', 'KAMAZ_PickupManualSpawnPreset_WheelsOnly']
LPRE = ['KAMAZ_Pickup_LaikaManualSpawnPreset', 'KAMAZ_Pickup_LaikaManualSpawnPreset_Full',
        'KAMAZ_Pickup_LaikaManualSpawnPreset_MinimalFunctional', 'KAMAZ_Pickup_LaikaManualSpawnPreset_WheelsOnly']
ALLPRE = KPRE + LPRE

# MIDWAY vehicles to merge into the manual spawn map (key class path, preset package path)
MW_VEHS = [
    ('/Game/ConZ_Files/Vehicles/Boat/Barba/Yacht/zzMIDWAY_BPC_Yacht.zzMIDWAY_BPC_Yacht_C',
     '/Game/ConZ_Files/Vehicles/SpawningPresets/ManualSpawn/zzMIDWAY_YachtManualSpawnPreset'),
    ('/Game/ConZ_Files/Vehicles/Airplane/Duster/V22Osprey/zzMIDWAY_BPC_V22_Osprey.zzMIDWAY_BPC_V22_Osprey_C',
     '/Game/ConZ_Files/Vehicles/SpawningPresets/ManualSpawn/zzMIDWAY_V22OspreyManualSpawnPreset'),
    ('/Game/ConZ_Files/Vehicles/Airplane/Duster/MH6Native/zzMIDWAY_BP_MH6_LittleBird.zzMIDWAY_BP_MH6_LittleBird_C',
     '/Game/ConZ_Files/Vehicles/SpawningPresets/ManualSpawn/zzMIDWAY_MH6ManualSpawnPreset'),
    ('/Game/ConZ_Files/Vehicles/Car/Rager/MidwayTruck/zzMIDWAY_BPC_MIDWAY_Kamaz.zzMIDWAY_BPC_MIDWAY_Kamaz_C',
     '/Game/ConZ_Files/Vehicles/SpawningPresets/ManualSpawn/zzMIDWAY_MWTruckManualSpawnPreset'),
    ('/Game/ConZ_Files/Vehicles/Bike/Motorcycle/Dirtbike/SpyHypersport/zzzzzMIDWAY_BPC_SpyHypersport.zzzzzMIDWAY_BPC_SpyHypersport_C',
     '/Game/ConZ_Files/Vehicles/SpawningPresets/ManualSpawn/SpyHypersport/zzzzzMIDWAY_SpyHypersportManualSpawnPreset'),
    ('/Game/ConZ_Files/Vehicles/Airplane/Duster/Mig29/zzzzzzMIDWAY_BPC_Mig29.zzzzzzMIDWAY_BPC_Mig29_C',
     '/Game/ConZ_Files/Vehicles/SpawningPresets/ManualSpawn/Mig29/zzzzzzMIDWAY_Mig29ManualSpawnPreset'),
]
MW_SRC = (r'C:\Users\leman\AppData\Local\Temp\rufp\midway_vm'
          r'\SCUM\Content\ConZ_Files\Vehicles')
mw_ue = open(MW_SRC + r'\BP_VehicleManager.uexp', 'rb').read()

new_names = ([VEH_K, VEH_L] + [PDIR + p for p in ALLPRE] + ALLPRE
             + [v for v, _ in MW_VEHS] + [p for _, p in MW_VEHS]
             + [p.rsplit('/', 1)[1] for _, p in MW_VEHS])
VEH_K_I, VEH_L_I = NC, NC + 1
PKG_I = NC + 2
SHRT_I = NC + 2 + 8
MW_VEH_I = NC + 18
MW_PRE_I = NC + 18 + len(MW_VEHS)
MWSHRT_I = MW_PRE_I + len(MW_VEHS)

def fstr(s):
    b = s.encode('ascii')
    return struct.pack('<i', len(b) + 1) + b + b'\x00'

names_blob = b''.join(fstr(s) + b'\x00\x00\x00\x00' for s in new_names)
DNAMES = len(names_blob)

KPKG_IMP = IC              # 108..115: our 8 pkg imports (outers)
KCLS_IMP = KPKG_IMP + 8    # 116..123: our 8 VehiclePreset class imports
MWPKG_IMP = KCLS_IMP + 8   # 124..129: MW 6 pkg imports (outers)
MWCLS_IMP = MWPKG_IMP + 6  # 130..135: MW 6 VehiclePreset class imports
new_imports = []
for i in range(8):
    new_imports.append((86, 0, 154, 0, 0, PKG_I + i, 0))
for i in range(8):
    # (cp,cpn,cn,cnn,outer,on,onn): link convention is standard UE: -k -> import k-1
    new_imports.append((89, 0, 189, 0, -(KPKG_IMP + i + 1), SHRT_I + i, 0))
for i in range(len(MW_VEHS)):
    new_imports.append((86, 0, 154, 0, 0, MW_PRE_I + i, 0))
for i in range(len(MW_VEHS)):
    # MIDWAY pairs each pkg import with a VehiclePreset class import; slots link the CLASS
    new_imports.append((89, 0, 189, 0, -(MWPKG_IMP + i + 1), MWSHRT_I + i, 0))
imports_blob = b''.join(struct.pack('<7i', *e) for e in new_imports)
DIMP = len(imports_blob)
LINK0 = -(KCLS_IMP + 1)    # -117 for KAMAZ base class
MWLINK0 = -(MWCLS_IMP + 1) # -131 for MIDWAY Yacht class

# ---------- entries ----------
def build_entry(src, donor_off, veh_idx, links):
    e = bytearray(src[donor_off:donor_off + 136])
    struct.pack_into('<i', e, 0, veh_idx)
    for j, lk in enumerate(links):
        struct.pack_into('<i', e, 12 + 29 * j + 25, lk)
    return bytes(e)

# class import i sits at table index 116+i -> link = -(116+i+2) = LINK0 - i
# KAMAZ donor Rager: ai0 base, ai1 MinFunc(i=2), ai2 Full(i=1), ai3 base
entry_k = build_entry(ue, 209 + 136 * 9, VEH_K_I, [LINK0, LINK0 - 2, LINK0 - 1, LINK0])
# Laika donor: ai0 base(i=4), ai1 MinFunc(i=6), ai2 Full(i=5), ai3 base
entry_l = build_entry(ue, 209 + 136 * 1, VEH_L_I, [LINK0 - 4, LINK0 - 6, LINK0 - 5, LINK0 - 4])
# MIDWAY entries 19..24 copied from their manager, one preset link in all 4 slots
mw_entries = b''.join(
    build_entry(mw_ue, 209 + 136 * (19 + i), MW_VEH_I + i, [MWLINK0 - i] * 4)
    for i in range(len(MW_VEHS)))

# ---------- uexp ----------
NUM_OFF = 205
MAP_END = 2793
assert i32(ue, NUM_OFF) == 19, 'map num mismatch'
new_ue = bytearray(ue[:NUM_OFF] + struct.pack('<i', 19 + 2 + len(MW_VEHS))
                   + ue[NUM_OFF + 4:MAP_END] + entry_k + entry_l + mw_entries + ue[MAP_END:])
DUE = len(new_ue) - len(ue)
assert i32(ue, 176) == 2592, 'map tag size offset mismatch'
struct.pack_into('<i', new_ue, 176, 2592 + DUE)   # MapProperty tag Size = 136*Num + 8

# ---------- uasset rebuild ----------
hdr1 = ua[:IOFF] + names_blob + ua[IOFF:EOFF] + imports_blob
exports_blob = b''
DHDR = DNAMES + DIMP + 4 * (8 + len(MW_VEHS))  # premap grows by 14 int32
for k, e in enumerate(exports):
    e = list(e)
    e[9] += DHDR               # SerialOffset absolute: uasset header grew (ALL exports)
    if k >= 2:
        e[9] += DUE            # uexp data shifted by inserted map entries
        e[21] += 8 + 6         # exp2..4 first-dep shifts by all 14 inserted premap ints
    if k == 1:
        e[7] += DUE            # SerialSize (i64 low dword)
        e[23] += 8 + 6         # d2 = CreateBeforeSerialization: all 14 class links stay here (proven)
    exports_blob += struct.pack('<26i', *e)
depends = ua[DEP:DEP + EC * 4]
ard = ua[ARD:ARD + 4]
premap = list(struct.unpack_from('<%di' % PCNT, ua, POFF))
assert len(premap) == 71
INS = 7 + 2 + 47                     # 56: after stock d1 and the 47 stock class imports (d2 tail)
new_premap = (premap[:INS] + [LINK0 - i for i in range(8)]
              + [MWLINK0 - i for i in range(len(MW_VEHS))] + premap[INS:])
premap_blob = struct.pack('<%di' % len(new_premap), *new_premap)

new_total = len(hdr1) + 104 * EC + len(depends) + len(ard) + len(premap_blob)

NADD = 18 + 3 * len(MW_VEHS)  # 2 veh + 8 pkg + 8 short + 6 mw veh + 6 mw path + 6 mw short
IADD = 16 + 2 * len(MW_VEHS)  # 8+8+6 pkg + 8+6 class
s = bytearray(ua[:IOFF])
struct.pack_into('<i', s, 41, NC + NADD)                     # NameCount
struct.pack_into('<i', s, 57, EC)                            # ExportCount
struct.pack_into('<i', s, 61, len(hdr1))                     # ExportOffset
struct.pack_into('<i', s, 65, IC + IADD)                     # ImportCount
struct.pack_into('<q', s, 169, BULK + DNAMES + DIMP + DUE)   # BulkDataStartOffset
struct.pack_into('<i', s, 185, len(new_premap))              # PreloadDependencyCount

new_ua = bytearray(hdr1 + exports_blob + depends + ard + premap_blob)
assert len(new_ua) == new_total, (len(new_ua), new_total)
struct.pack_into('<i', new_ua, 24, new_total)                # TotalHeaderSize
struct.pack_into('<i', new_ua, 41, NC + NADD)                # NameCount
struct.pack_into('<i', new_ua, 61, len(hdr1))                # ExportOffset
struct.pack_into('<i', new_ua, 65, IC + IADD)                # ImportCount
struct.pack_into('<i', new_ua, 69, IOFF + DNAMES)            # ImportOffset
struct.pack_into('<i', new_ua, 73, DEP + DNAMES + DIMP)      # DependsOffset
struct.pack_into('<q', new_ua, 169, len(new_ua) + len(new_ue) - 4)  # BulkDataStartOffset
struct.pack_into('<i', new_ua, 165, ARD + DNAMES + DIMP)     # AssetRegistryDataOffset
struct.pack_into('<i', new_ua, 185, len(new_premap))         # PreloadDependencyCount
struct.pack_into('<i', new_ua, 189, POFF + DNAMES + DIMP)    # PreloadDependencyOffset

open(OUT + r'\BP_VehicleManager.uasset', 'wb').write(new_ua)
open(OUT + r'\BP_VehicleManager.uexp', 'wb').write(new_ue)
print('uasset %d -> %d (dnames=%d dimp=%d)' % (len(ua), len(new_ua), DNAMES, DIMP))
print('uexp   %d -> %d (due=%d)' % (len(ue), len(new_ue), DUE))
print('new name idx: veh K=%d L=%d, pkg=%d..%d, short=%d..%d, mw veh=%d..%d, mw pre=%d..%d' % (
    VEH_K_I, VEH_L_I, PKG_I, PKG_I + 7, SHRT_I, SHRT_I + 7,
    MW_VEH_I, MW_VEH_I + len(MW_VEHS) - 1, MW_PRE_I, MW_PRE_I + len(MW_VEHS) - 1))
print('new import links: ours %d..%d, midway %d..%d' % (
    LINK0, LINK0 - 7, MWLINK0, MWLINK0 - (len(MW_VEHS) - 1)))
print('map entries: %d, premap: %d' % (19 + 2 + len(MW_VEHS), len(new_premap)))
print('OK written to', OUT)
