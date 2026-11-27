"""osm_exp3.txt 읽기: 레코드 = 종류+id;태그;구글 polyline(1e-5)!  → EPSG:5179 (m)"""
import pyproj, json
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import unary_union
TR = pyproj.Transformer.from_crs(4326, 5179, always_xy=True)
INV = pyproj.Transformer.from_crs(5179, 4326, always_xy=True)
def dec(s):
    out, i, la, lo = [], 0, 0, 0
    while i < len(s):
        vals = []
        for _ in range(2):
            r = sh = 0
            while True:
                b = ord(s[i]) - 63; i += 1; r |= (b & 0x1f) << sh; sh += 5
                if b < 0x20: break
            vals.append(~(r >> 1) if r & 1 else r >> 1)
        la += vals[0]; lo += vals[1]; out.append((la / 1e5, lo / 1e5))
    return out
def load(path='osm_exp3.txt'):
    R = []
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line: continue
        assert line.endswith('!'), line[:40]
        a = line[:-1].split(';'); kid, tg, poly = a[0], a[1], ';'.join(a[2:])
        tags = {}
        for kv in tg.split(','):
            if ':' in kv:
                k, v = kv.split(':', 1)
                # keys like footway:sidewalk / building:levels: split on first ':' is wrong for those
                tags[k] = v
        pts = dec(poly); xy = [TR.transform(lo, la) for la, lo in pts]
        R.append(dict(kind=kid[0], id=kid[1:], tags=tags, raw=tg, xy=xy))
    return R
def tagval(raw, key):
    # raw tag string "highway:footway,footway:sidewalk,..." — find exact key
    for kv in raw.split(','):
        if kv.startswith(key + ':'): return kv[len(key) + 1:]
    return None
