import struct, sys, os
sys.stdout.reconfigure(errors='replace')

# usage: asset_registry_merge.py [ours.bin theirs.bin out.bin]
OURS = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\leman\AppData\Local\Temp\rufp\KAMAZ_AssetRegistry.bin.bak'
THEIRS = sys.argv[2] if len(sys.argv) > 2 else r'C:\Users\leman\AppData\Local\Temp\rufp\ar86\SCUM\AssetRegistry.bin'
OUT = sys.argv[3] if len(sys.argv) > 3 else r'C:\Users\leman\AppData\Local\Temp\rufp\AssetRegistry_merged.bin'
MW_PKG_PAT = ('MIDWAY', 'MWNet', 'WILDWeaponKit')

class R:
    def __init__(s, d):
        s.d = d; s.p = 0
    def rd(s, fmt, n):
        v = struct.unpack_from(fmt, s.d, s.p)[0]; s.p += n; return v
    def u8(s): return s.rd('<B', 1)
    def i32(s): return s.rd('<i', 4)
    def u32(s): return s.rd('<I', 4)
    def u64(s): return s.rd('<Q', 8)
    def i64(s): return s.rd('<q', 8)
    def raw(s, n):
        b = s.d[s.p:s.p+n]; s.p += n; return b
    def fname(s):
        idx = s.u32()
        if idx & 0x80000000:
            return (idx & 0x7FFFFFFF, s.u32())
        return (idx, 0)
    def fstring_raw(s):
        ln = s.i32()
        n = ln if ln >= 0 else -ln * 2
        return (ln, s.raw(n))

def parse(path):
    d = open(path, 'rb').read()
    r = R(d)
    assert (r.u32(), r.u32(), r.u32(), r.u32()) == (0x717F9EE7, 0xE9B0493A, 0x88B39132, 0x1B388107)
    version = r.i32()
    assert version == 8, version
    nameCount = r.i32()
    numStringBytes = r.u32()
    hashVersion = r.u64()
    hashes = list(struct.unpack_from('<%dQ' % nameCount, d, 36))
    r.p = 36 + 8 * nameCount
    headers = list(struct.unpack_from('<%dH' % nameCount, d, r.p))
    r.p += 2 * nameCount
    strings_blob = r.raw(numStringBytes)
    spans = []
    off = 0
    names = []
    for v in headers:
        l = ((v & 0x7F) << 8) | (v >> 8)
        bl = l * 2 if v & 0x80 else l
        spans.append((off, bl))
        names.append(strings_blob[off:off+bl].decode('utf-16-le' if v & 0x80 else 'latin1'))
        off += bl
    assert off == numStringBytes
    store_off = r.p
    magic = r.u32()
    nums = [r.i32() for _ in range(11)]
    skip4 = r.raw(4)
    print(f'  parse[{os.path.basename(path)}]: store@{store_off:X} nums={nums}')
    texts_raw = [r.fstring_raw() for _ in range(nums[4])]
    nnames = [r.u32() for _ in range(nums[0])]
    snames = [r.fname() for _ in range(nums[1])]
    nep = [r.raw(12) for _ in range(nums[2])]
    ep = [(r.fname(), r.fname(), r.fname()) for _ in range(nums[3])]
    ansi_off = [r.u32() for _ in range(nums[5])]
    wide_off = [r.u32() for _ in range(nums[6])]
    ansi_bytes = r.raw(nums[7])
    wide_bytes = r.raw(nums[8] * 2)
    npairs = [(r.u32(), r.u32()) for _ in range(nums[9])]
    pairs = [(r.fname(), r.u32()) for _ in range(nums[10])]
    endpos = r.p
    assert r.u32() == 0x87654321, (hex(endpos), 'END magic')
    print(f'  parse: store_end@{endpos:X} ok')
    assets = []
    acount = r.i32()
    for k in range(acount):
        try:
            rs = r.p
            rec = {
                'op': r.fname(), 'pp': r.fname(), 'cls': r.fname(),
                'pn': r.fname(), 'an': r.fname(),
                'handle': r.u64(),
                'bundles': [],
            }
            nb = r.i32()
            for _ in range(nb):
                bname = r.fname()
                na = r.i32()
                items = []
                for _ in range(na):
                    items.append((r.fname(), r.fstring_raw()))
                rec['bundles'].append((bname, items))
            ck = r.i32()
            rec['chunks_cnt'] = ck
            rec['chunks_data'] = r.raw(ck * 4)
            rec['flags'] = r.u32()
            if nb > 4096 or ck > 4096 or rs + 44 > r.p + 100000 or r.p - rs > 100000:
                print(f'  SUSPICIOUS asset {k}: start={rs:X} end={r.p:X} nb={nb} ck={ck} handle={rec["handle"]:#x}')
        except struct.error:
            print(f'  parse: FAIL at asset {k}/{acount} pos={r.p:X}')
            raise
        assets.append(rec)
    dep_size = r.i64()
    dep_raw = r.raw(dep_size)
    pcount = r.i32()
    pkgdata = []
    for _ in range(pcount):
        pn = r.fname()
        disk = r.i64()
        guid = r.raw(16)
        hv = r.u32()
        chash = r.raw(16) if hv else b''
        pkgdata.append((pn, disk, guid, hv, chash))
    assert r.p == len(d), (r.p, len(d))
    return {
        'names': names, 'spans': spans, 'headers': headers, 'hashes': hashes,
        'strings_blob': strings_blob, 'nums': nums, 'magic': magic, 'skip4': skip4,
        'texts_raw': texts_raw, 'nnames': nnames, 'snames': snames,
        'nep': nep, 'ep': ep, 'ansi_off': ansi_off, 'wide_off': wide_off,
        'ansi_bytes': ansi_bytes, 'wide_bytes': wide_bytes,
        'npairs': npairs, 'pairs': pairs,
        'assets': assets, 'dep_raw': dep_raw, 'dep_size': dep_size, 'pkgdata': pkgdata,
        'nameCount': nameCount, 'hashVersion': hashVersion,
    }

def w():
    out = bytearray()

    def wf(fmt, *vals):
        out.extend(struct.pack(fmt, *vals))
    return out, wf

ours = parse(OURS)
their = parse(THEIRS)
print(f'ours: names={ours["nameCount"]} assets={len(ours["assets"])} nums={ours["nums"]} pkgdata={len(ours["pkgdata"])}')
print(f'their: names={their["nameCount"]} assets={len(their["assets"])} nums={their["nums"]} pkgdata={len(their["pkgdata"])}')

o_names = ours['names']
name_to_idx = {}
for i, s in enumerate(o_names):
    if s not in name_to_idx:
        name_to_idx[s] = i

new_hashes = []
new_headers = []
new_spans = []
their2new = {}

def intern_name(idx):
    if idx in their2new:
        return their2new[idx]
    s = their['names'][idx]
    if s in name_to_idx:
        their2new[idx] = name_to_idx[s]
        return name_to_idx[s]
    ni = len(o_names) + len(new_hashes)
    name_to_idx[s] = ni
    their2new[idx] = ni
    new_hashes.append(their['hashes'][idx])
    new_headers.append(their['headers'][idx])
    new_spans.append(their['spans'][idx])
    return ni

def remap_fn(f):
    return (intern_name(f[0]), f[1])

def remap_val(v):
    t = v & 7
    base = {0: ours['nums'][5], 1: ours['nums'][6], 2: ours['nums'][0],
            3: ours['nums'][1], 4: ours['nums'][2], 5: ours['nums'][3], 6: ours['nums'][4]}[t]
    return (((v >> 3) + base) << 3) | t

# pre-pass: referenced their names (assets, npairs, bundles, pkgdata)
o_assets_ident = set()
for a in ours['assets']:
    o_assets_ident.add((o_names[a['pn'][0]], o_names[a['an'][0]]))

their_unique = []
for a in their['assets']:
    ident = (their['names'][a['pn'][0]], their['names'][a['an'][0]])
    if ident not in o_assets_ident:
        their_unique.append(a)
print(f'their assets: {len(their["assets"])}, unique: {len(their_unique)}')

for a in their_unique:
    for k in ('op', 'pp', 'cls', 'pn', 'an'):
        intern_name(a[k][0])
    for bn, items in a['bundles']:
        intern_name(bn[0])
for key, val in their['npairs']:
    intern_name(key)
mw_pkgdata = []
for pn, disk, guid, hv, chash in their['pkgdata']:
    s = their['names'][pn[0]]
    if any(p in s for p in MW_PKG_PAT):
        mw_pkgdata.append((pn, disk, guid, hv, chash))
        intern_name(pn[0])
print(f'their pkgdata: {len(their["pkgdata"])}, MW-unique: {len(mw_pkgdata)}')

# serialize
out = bytearray()
def wf(fmt, *vals):
    out.extend(struct.pack(fmt, *vals))

wf('<IIII', 0x717F9EE7, 0xE9B0493A, 0x88B39132, 0x1B388107)
newNameCount = ours['nameCount'] + len(new_hashes)
newStrBytes = len(ours['strings_blob']) + sum(b for _, b in new_spans)
wf('<iiI', 8, newNameCount, newStrBytes)
wf('<Q', ours['hashVersion'])
for h in ours['hashes']:
    wf('<Q', h)
for h in new_hashes:
    wf('<Q', h)
for v in ours['headers']:
    wf('<H', v)
for v in new_headers:
    wf('<H', v)
out.extend(ours['strings_blob'])
for off, bl in new_spans:
    out.extend(their['strings_blob'][off:off+bl])

# FStore
assert ours['magic'] == 0x12345679 == their['magic']
wf('<I', ours['magic'])
nn = ours['nums'][:]

def add_to(k, n):
    nn[k] += n

add_to(5, len(their['ansi_off']))
add_to(6, len(their['wide_off']))
add_to(7, len(their['ansi_bytes']))
add_to(8, len(their['wide_bytes']) // 2)
add_to(9, len(their['npairs']))
for v in nn:
    wf('<i', v)
out.extend(ours['skip4'])
for ln, data in ours['texts_raw']:
    wf('<i', ln)
    out.extend(data)
for v in ours['nnames']:
    wf('<I', v)
def wfn(f):
    if f[1]:
        wf('<II', f[0] | 0x80000000, f[1])
    else:
        wf('<I', f[0])
for f in ours['snames']:
    wfn(f)
for raw in ours['nep']:
    out.extend(raw)
for c, o_, p in ours['ep']:
    wfn(c); wfn(o_); wfn(p)
for v in ours['ansi_off']:
    wf('<I', v)
for v in ours['wide_off']:
    wf('<I', v)
out.extend(ours['ansi_bytes'])
out.extend(ours['wide_bytes'])
for k, v in ours['npairs']:
    wf('<II', k, v)
for f, v in ours['pairs']:
    wfn(f); wf('<I', v)
# appended: their store tables (names/nep/ep/texts empty in theirs)
for v in their['ansi_off']:
    wf('<I', v)
for v in their['wide_off']:
    wf('<I', v)
out.extend(their['ansi_bytes'])
out.extend(their['wide_bytes'])
for k, v in their['npairs']:
    wf('<II', intern_name(k), remap_val(v))
for f, v in their['pairs']:
    wfn(remap_fn(f)); wf('<I', remap_val(v))
wf('<I', 0x87654321)

# assets
wf('<i', len(ours['assets']) + len(their_unique))

def wasset(a, names_theirs):
    gt = (lambda f: f) if not names_theirs else remap_fn
    for k in ('op', 'pp', 'cls', 'pn', 'an'):
        wfn(gt(a[k]))
    h = a['handle']
    if names_theirs:
        if h >> 63:
            num = (h >> 32) & 0xFFFF
            begin = (h & 0xFFFFFFFF) + ours['nums'][9]
            wf('<Q', (1 << 63) | (num << 32) | begin)
        else:
            num = (h >> 32) & 0xFFFF
            begin = (h & 0xFFFFFFFF) + ours['nums'][10]
            wf('<Q', (num << 32) | begin)
    else:
        wf('<Q', h)
    wf('<i', len(a['bundles']))
    for bn, items in a['bundles']:
        wfn(gt(bn))
        wf('<i', len(items))
        for f, (ln, data) in items:
            wfn(gt(f))
            wf('<i', ln)
            out.extend(data)
    wf('<i', a['chunks_cnt'])
    out.extend(a['chunks_data'])
    wf('<I', a['flags'])

asset0 = len(out)
for a in ours['assets']:
    wasset(a, False)
for a in their_unique:
    wasset(a, True)
asset_bytes = len(out) - asset0

# deps (ours; empty in both)
wf('<q', ours['dep_size'])
out.extend(ours['dep_raw'])

# pkgdata: ours + MW-unique from theirs
wf('<i', len(ours['pkgdata']) + len(mw_pkgdata))
for pn, disk, guid, hv, chash in ours['pkgdata']:
    wfn(pn); wf('<q', disk); out.extend(guid); wf('<I', hv)
    if hv: out.extend(chash)
for pn, disk, guid, hv, chash in mw_pkgdata:
    wfn(remap_fn(pn)); wf('<q', disk); out.extend(guid); wf('<I', hv)
    if hv: out.extend(chash)

open(OUT, 'wb').write(out)
print(f'names: {newNameCount} (added {len(new_hashes)})')
print(f'strings: {newStrBytes} (added {newStrBytes - len(ours["strings_blob"])})')
print(f'nums: {nn}')
print(f'assets written: {len(ours["assets"])} + {len(their_unique)} = {len(ours["assets"]) + len(their_unique)}')
print(f'size: {len(out)} (ours {len(open(OURS,"rb").read())}, theirs {len(open(THEIRS,"rb").read())})')
