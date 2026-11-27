"""KSPO DOME과 이어진 걸을 수 있는 길 전부(검증용 별도 층).
- 구역: X 966880~967420, Y 1946330~1946920 (EPSG:5179, 돔·한얼광장·만남의광장·올림픽공원역 쪽)
- 1 기존: v3에서 칠한 칸(OSM 보행로·광장 × 잰 폭 + 사진에서 찾은 광장)
- 2 사진 포장: v3 '확인 필요'(주차장·차도 옆 사진 포장면)를 이번엔 칠함
- 3 새로 칠한 길: OSM 길 중 v3에서 뺀 것(차량 통로 service·주차장 통로, 공원 경계 밖 보도)을 칠함. 폭은 OSM 폭 태그, 없으면 종류별 기본(차량 통로 6m)
- 건물·물은 뺌. 칸 안 면적 1㎡ 이상이면 칠함. 돔 둘레 15m 안 칸에서 출발해 8방향으로 이어진 칸만 남김."""
import sys, json, numpy as np, shapely, zlib, base64; sys.path.insert(0, '.')
import osm
from shapely.geometry import LineString, Polygon, box
R = osm.load('osm_exp3.txt'); v3 = np.load('cells_v3.npy'); W, H = 315, 294; X0 = 965500 + 69 * 5; Y0 = 1945750 + 41 * 5
XA, XB, YA, YB = 966880, 967420, 1946330, 1946920
i0, i1, j0, j1 = (XA - X0) // 5, (XB - X0) // 5, (YA - Y0) // 5, (YB - Y0) // 5
DEF = {'footway': 2.8, 'path': 1.5, 'steps': 2.5, 'cycleway': 3, 'service': 6, 'pedestrian': 5, 'living_street': 5}
BB = box(XA - 50, YA - 50, XB + 50, YB + 50)
poly = lambda r: Polygon(r['xy']) if len(r['xy']) >= 3 and r['xy'][0] == r['xy'][-1] else None
geo, added = [], []
for r in R:
    if r['kind'] == 'H':
        hw = osm.tagval(r['raw'], 'highway'); g = LineString(r['xy'])
        if hw not in DEF or not g.intersects(BB): continue
        w = osm.tagval(r['raw'], 'width'); w = float(w) if w else DEF[hw]
        geo.append(g.buffer(w / 2, cap_style=2, join_style=2)); added.append((r['id'], hw, w, round(g.intersection(box(XA, YA, XB, YB)).length)))
    elif r['kind'] == 'A':
        p = poly(r)
        if p is not None and p.intersects(BB): geo.append(p.buffer(0))
U = shapely.union_all(geo)
EXC = shapely.union_all([p.buffer(0) for r in R if (r['kind'] in 'BLW' or (r['kind'] == 'R' and 'role:outer' in r['raw'])) and (p := poly(r)) is not None and p.intersects(BB)])
U = U.difference(EXC)
ii, jj = np.meshgrid(np.arange(i0, i1), np.arange(j0, j1)); ii, jj = ii.ravel(), jj.ravel()
cells = shapely.box(X0 + ii * 5, Y0 + jj * 5, X0 + ii * 5 + 5, Y0 + jj * 5 + 5)
area = shapely.area(shapely.intersection(cells, U))
L = np.zeros((H, W), np.uint8)
lvl = lambda a: 1 if a < 5 else 2 if a < 10 else 3 if a < 15 else 4 if a < 20 else 5
for k in range(len(ii)):
    i, j = ii[k], jj[k]; v = v3[j, i]
    if 1 <= v <= 20: L[j, i] = 10 + ((v - 1) % 5) + 1           # 1 기존 (11~15)
    elif 21 <= v <= 25: L[j, i] = 20 + ((v - 1) % 5) + 1        # 2 사진 포장 (21~25)
    elif area[k] >= 1: L[j, i] = 30 + lvl(area[k])               # 3 새로 칠한 길 (31~35)
# 돔에서 이어진 칸만
dome = Polygon([r for r in R if 'name:올림픽체조경기장' in r['raw']][0]['xy'])
ring = dome.buffer(15).difference(dome)
seed = [(j, i) for j in range(j0, j1) for i in range(i0, i1) if L[j, i] and ring.intersects(box(X0 + i * 5, Y0 + j * 5, X0 + i * 5 + 5, Y0 + j * 5 + 5))]
keep = np.zeros_like(L, bool); st = list(seed)
for s in st: keep[s] = True
while st:
    j, i = st.pop()
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            a, b = j + dj, i + di
            if j0 <= a < j1 and i0 <= b < i1 and L[a, b] and not keep[a, b]: keep[a, b] = True; st.append((a, b))
L[~keep] = 0
np.save('dome_layer.npy', L)
c = zlib.compressobj(9, zlib.DEFLATED, -15); b = c.compress(L.tobytes()) + c.flush(); open('dome_layer.b64', 'w').write(base64.urlsafe_b64encode(b).decode().rstrip('='))
mid = {1: 2.5, 2: 7.5, 3: 12.5, 4: 17.5, 5: 22.5}
for cat, nm in ((1, '기존'), (2, '사진 포장(확인 필요였던 곳)'), (3, '새로 칠한 길')):
    m = (L // 10) == cat; print(nm, int(m.sum()), '칸, 보행 면적 약', round(sum(mid[int(x) % 10] for x in L[m])), '㎡')
print('돔 둘레 출발 칸', len(seed), '| 구역 안 칠한 칸 전체', int((L > 0).sum()), '| 이어지지 않아 뺀 칸', int(((L == 0) & False).sum()))
# 새로 칠한 길에 들어간 OSM 길(차량 통로)
print([a for a in added if a[1] in ('service', 'living_street') and a[3] > 0])
