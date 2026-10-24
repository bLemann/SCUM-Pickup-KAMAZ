import struct, sys
sys.stdout.reconfigure(errors='replace')

PATH = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\leman\AppData\Local\Temp\rufp\KAMAZ_AssetRegistry.bin.bak'
d = open(PATH, 'rb').read()
n = len(d)
pos = 0

def rd(fmt, size):
    global pos
    v = struct.unpack_from(fmt, d, pos)[0]
    pos += size
    return v

def u8():  return rd('<B', 1)
def i32(): return rd('<i', 4)
def u32(): return rd('<I', 4)
def i64(): return rd('<q', 8)
def u64(): return rd('<Q', 8)

def fname():
    idx = u32()
    num = 0
    if idx & 0x80000000:
        idx &= 0x7FFFFFFF
        num = u32()
    return (idx, num)

def fstring():
    global pos
    ln = i32()
    if ln < 0:
        raw = d[pos:pos - ln * 2]
        pos += -ln * 2
        return raw.decode('utf-16-le', 'replace').rstrip('\x00')
    raw = d[pos:pos + ln]
    pos += ln
    return raw[:max(0, ln - 1)].decode('latin1')

guid = (u32(), u32(), u32(), u32())
assert guid == (0x717F9EE7, 0xE9B0493A, 0x88B39132, 0x1B388107), 'bad magic'
version = i32()
nameCount = i32()
numStringBytes = u32()
hashVersion = u64()
hashes_off = pos; pos += 8 * nameCount
hdrs_off = pos; pos += 2 * nameCount
strings_off = pos; pos += numStringBytes
print(f'version={version} names={nameCount} strBytes={numStringBytes}')
print(f'hashes@0x{hashes_off:X} headers@0x{hdrs_off:X} strings@0x{strings_off:X} fstore@0x{pos:X}')

hdrs = struct.unpack_from('<%dH' % nameCount, d, hdrs_off)
lens = [((v & 0x7F) << 8) | (v >> 8) for v in hdrs]
blens = [l * 2 if v & 0x80 else l for v, l in zip(hdrs, lens)]
print('name lens sum:', sum(blens), '== numStringBytes?', sum(blens) == numStringBytes)
utf16_cnt = sum(1 for v in hdrs if v & 0x80)
print('utf16 names:', utf16_cnt)

names = []
off = 0
for v, bl in zip(hdrs, blens):
    l = bl // (2 if v & 0x80 else 1)
    names.append(d[strings_off + off: strings_off + off + bl].decode('utf-16-le' if v & 0x80 else 'latin1'))
    off += bl

def nstr(f):
    idx, num = f
    s = names[idx] if 0 <= idx < len(names) else f'<BAD {idx}>'
    return s + ('-%d' % num if num else '')

store_off = pos
magic = u32()
order = {0x12345678: 'Member', 0x12345679: 'TextFirst'}.get(magic, 'BAD 0x%X' % magic)
nums = [i32() for _ in range(11)]
print(f'store@0x{store_off:X} magic={order} nums={nums}')

if order == 'TextFirst':
    pos += 4  # CUE4Parse FStore TextFirst: Ar.Position += 4 before Texts
    texts = [fstring() for _ in range(nums[4])]
numberless_names = [u32() for _ in range(nums[0])]
store_names = [fname() for _ in range(nums[1])]
nep = [(u32(), u32(), u32()) for _ in range(nums[2])]
ep = [(fname(), fname(), fname()) for _ in range(nums[3])]
ansi_off = [u32() for _ in range(nums[5])]
wide_off = [u32() for _ in range(nums[6])]
ansi_off_pos = pos; pos += nums[7]
wide_off_pos = pos; pos += nums[8] * 2
npairs_pos = pos; pos += nums[9] * 8
pairs_pos = pos
for _ in range(nums[10]):
    fname(); u32()
end_magic = u32()
print(f'END magic ok? {end_magic == 0x87654321} store_end=0x{pos:X}')
print('texts:', texts)
print('sample store names:', [nstr(x) for x in store_names[:5]])

asset_count = i32()
print(f'assets={asset_count} @0x{pos:X}')
rec_info = []
for k in range(asset_count):
    rs = pos
    old_path = fname()
    pkg_path = fname()
    asset_class = fname()
    pkg_name = fname()
    asset_name = fname()
    map_size = u64()
    nb = i32()
    for _ in range(nb):
        fname()
        na = i32()
        for _ in range(na):
            fname()
            if version >= 14: fname()
            fstring()
    ck = i32(); pos += ck * 4
    flags = u32()
    if k < 3 or k >= asset_count - 2:
        rec_info.append((k, nstr(pkg_name) + '.' + nstr(asset_name), nstr(asset_class), map_size, rs, pos - rs))
print('first/last assets:')
for r in rec_info:
    print('  ', r)

dep_off = pos
dep_size = i64()
dep_cnt = i32()
dep_end = dep_off + 8 + dep_size
print(f'deps@0x{dep_off:X} size={dep_size} nodes={dep_cnt} end=0x{dep_end:X}')
max_node_ref = 0
for k in range(dep_cnt):
    fb = u8()
    if fb & 1: fname()
    if fb & 2: fname()
    if fb & 4: fname()
    if fb & 8: fname()
    cnt = i32(); pd = [i32() for _ in range(cnt)]
    if cnt: pos += ((5 * cnt + 31) // 32) * 4
    cnt = i32(); nd = [i32() for _ in range(cnt)]
    cnt = i32(); md = [i32() for _ in range(cnt)]
    if cnt: pos += ((1 * cnt + 31) // 32) * 4
    cnt = i32(); rf = [i32() for _ in range(cnt)]
    for arr in (pd, nd, md, rf):
        if arr: max_node_ref = max(max_node_ref, max(arr))
print('deps walk pos=0x%X expected_end=0x%X match? %s maxnoderef=%d' % (pos, dep_end, pos == dep_end, max_node_ref))

pkg_count = i32()
print(f'packagedata={pkg_count} @0x{pos:X}')
pkg_seen = 0
for k in range(pkg_count):
    pn = fname()
    pos += 8
    pos += 16
    if u32(): pos += 16
    if pkg_seen < 3 or pkg_seen >= pkg_count - 3:
        print('  pkg:', nstr(pn))
    pkg_seen += 1
print('pkgdata pos=0x%X filesize=0x%X match? %s' % (pos, n, pos == n))
