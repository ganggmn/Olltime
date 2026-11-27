import pyproj
TR = pyproj.Transformer.from_crs(4326, 5179, always_xy=True)
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
        la += vals[0]; lo += vals[1]; out.append((la / 1e6, lo / 1e6))
    return out
def load(path='osm_dome.txt'):
    R = []
    import re
    for rec in re.split(r'~(?=[nw]\d)', open(path, encoding='utf-8').read().rstrip('\n')):
        tid, tg, poly = rec.split('|', 2)
        tags = dict(kv.split('=', 1) for kv in tg.split('^') if '=' in kv)
        pts = dec(poly); xy = [TR.transform(lo, la) for la, lo in pts]
        R.append(dict(type=tid[0], id=tid[1:], tags=tags, xy=xy))
    return R
