"""세 구역 칸 목록을 만들어요: 공원 안(KSPO DOME 칸 따로), 역→공원 통로(역마다), 테두리(공원 칸에서 750m 안, 동서남북).
zones3.py와 같은 규칙이에요. 사용: data 폴더에서 python3 ../analysis/zone_cells.py → checks/zone_cells_2025.json, ~/zone_cells.txt"""
import pandas as pd, numpy as np, glob, json, math, os, warnings; warnings.filterwarnings('ignore')
def inv(E, N):
    a = 6378137.0; f = 1 / 298.257222101; k0 = 0.9996; lat0 = math.radians(38); lon0 = math.radians(127.5); FE = 1e6; FN = 2e6
    e2 = 2 * f - f * f; ep2 = e2 / (1 - e2)
    def M(p): return a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * p - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * p) + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * p) - (35 * e2 ** 3 / 3072) * math.sin(6 * p))
    M1 = M(lat0) + (N - FN) / k0; mu = M1 / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256)); e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    p1 = mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu) + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
    C1 = ep2 * math.cos(p1) ** 2; T1 = math.tan(p1) ** 2; N1 = a / math.sqrt(1 - e2 * math.sin(p1) ** 2); R1 = a * (1 - e2) / (1 - e2 * math.sin(p1) ** 2) ** 1.5; D_ = (E - FE) / (N1 * k0)
    lat = p1 - (N1 * math.tan(p1) / R1) * (D_ * D_ / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 * C1 - 9 * ep2) * D_ ** 4 / 24)
    lon = lon0 + (D_ - (1 + 2 * T1 + C1) * D_ ** 3 / 6) / math.cos(p1)
    return math.degrees(lat), math.degrees(lon)
fr = []
for f in sorted(glob.glob('livingpop_grid/2025??.csv')):
    d = pd.read_csv(f, dtype=str, encoding='utf-8-sig', usecols=['hour', 'cell', 'total']); d['c'] = d.cell.str[-8:]; d = d[d.c.str.fullmatch(r'\d{8}')]
    e = d.c.str[:4].astype(int); n = d.c.str[4:].astype(int); d = d[(e >= 6400) & (e <= 7050) & (n >= 4350) & (n <= 4900)]
    d['v'] = pd.to_numeric(d.total, errors='coerce').fillna(0); d['h'] = d.hour.astype(int); fr.append(d[['h', 'c', 'v']])
G = pd.concat(fr)
cells = {c: inv(900000 + int(c[:4]) * 10 + 125, 1900000 + int(c[4:]) * 10 + 125) for c in G.c.unique()}
xy = lambda la, lo: (lo * 88200, la * 110900)
night = G[G.h.isin([2, 3, 4])].groupby('c').v.median(); dayv = G[G.h.isin([12, 13, 14, 15])].groupby('c').v.median()
park0 = {c for c, (la, lo) in cells.items() if 37.5125 <= la <= 37.5265 and 127.1155 <= lo <= 127.1320 and night.get(c, 0) < 300 and dayv.get(c, 0) >= 60}
# 공원 경계(서울시 '올림픽공원' 영역)와 절반 넘게 겹치는 칸도 공원으로 봐요. 88잔디마당·올림픽홀·올림픽파크텔 칸이 밤 인구 300명 남짓이라 위 규칙에서 빠졌었어요.
# 다만 밤에도 1,500명 넘게 있는 칸(아파트가 대부분)은 테두리로 둬요. 테두리 750m는 처음 규칙(park0) 기준이라 뽑아 둔 73칸이 그대로예요.
frac = json.load(open('checks/poi127_overlap.json', encoding='utf-8'))['frac']
park = park0 | {c for c in cells if frac.get(c, 0) >= 0.5 and night.get(c, 0) < 1500}
STN = {'올림픽공원': (37.516235, 127.130605), '몽촌토성': (37.517409, 127.112359), '한성백제': (37.516404, 127.116503)}
dist = lambda a, b: math.dist(xy(*a), xy(*b))
def seg_d(p, a, b):
    P, A, B = np.array(xy(*p)), np.array(xy(*a)), np.array(xy(*b)); t = np.clip(np.dot(P - A, B - A) / max(1e-9, np.dot(B - A, B - A)), 0, 1); return float(np.linalg.norm(P - (A + t * (B - A))))
corr = {}
for s, p in STN.items():
    sc = min(cells, key=lambda c: dist(cells[c], p)); near = min(park0, key=lambda c: dist(cells[c], p))
    zs = {c for c in cells if (c == sc or seg_d(cells[c], p, cells[near]) <= 150)}
    corr[s] = zs - (park0 - {sc}) if sc in park0 else zs - park0
allc = set().union(*corr.values()); inside = park - allc
P = np.array([xy(*cells[c]) for c in park0]); cx, cy = P.mean(0)
out = {}
for c, (la, lo) in cells.items():
    if c in inside: z, q = ('DOME' if c == '67004650' else '공원 안'), ''
    elif c in allc: z, q = '통로', [s for s, v in corr.items() if c in v][0]
    else:
        dm = min(dist(cells[c], cells[k]) for k in park0)
        if dm > 750: continue
        x, y = xy(la, lo); ang = math.degrees(math.atan2(y - cy, x - cx))
        z, q = '테두리', ('동' if -45 <= ang < 45 else '북' if 45 <= ang < 135 else '남' if -135 <= ang < -45 else '서')
    out[c] = dict(z=z, q=q, frac=round(frac.get(c, 0), 2), la=round(la, 5), lo=round(lo, 5), night=round(float(night.get(c, 0))), day=round(float(dayv.get(c, 0))))
json.dump(out, open('checks/zone_cells_2025.json', 'w'), ensure_ascii=False, indent=0)
open(os.path.expanduser('~/zone_cells.txt'), 'w').write('\n'.join(sorted(out)) + '\n')
import collections
print(len(out), collections.Counter((v['z'], v['q']) for v in out.values()))
