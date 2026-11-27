"""KSPO DOME과 이어진 걸을 수 있는 길 전부(검증용 별도 층).
- 구역: X 966880~967420, Y 1946330~1946920 (EPSG:5179, 돔·한얼광장·만남의광장·올림픽공원역 쪽)
- 1 기존: v3에서 칠한 칸(OSM 보행로·광장 × 잰 폭 + 사진에서 찾은 광장)
- 2 사진 포장: v3 '확인 필요'(주차장·차도 옆 사진 포장면)를 이번엔 칠함
- 3 새로 칠한 길: OSM 길 중 v3에서 뺀 것(돔 동쪽 주차장 통로·한체대 정문 다리 쪽 통로)을 칠함. 폭은 OSM 폭 태그, 없으면 종류별 기본(통로 6m). 공원 안 큰 차도(688650627)는 빼고 아래 '차도'로
- 건물·물은 뺌. 칸 안 면적 1㎡ 이상이면 칠함. 돔 둘레 15m 안 칸에서 출발해 8방향으로 이어진 칸만 남김.
- 4 못 지나감(41)·5 차도(51)·6 넘을 수 없는 선(dome_barriers.json): 아래 설명. 선을 가로지르는 칸 사이 이동은 막고, 그 때문에 돔과 끊긴 칸은 뺌(차도 폭 안이면 차도로)."""
import sys, json, numpy as np, shapely, zlib, base64; sys.path.insert(0, '.')
import osm
from shapely.geometry import LineString, Polygon, box
R = osm.load('osm_exp3.txt'); v3 = np.load('cells_v3.npy'); W, H = 315, 294; X0 = 965500 + 69 * 5; Y0 = 1945750 + 41 * 5
XA, XB, YA, YB = 966880, 967420, 1946330, 1946920
i0, i1, j0, j1 = (XA - X0) // 5, (XB - X0) // 5, (YA - Y0) // 5, (YB - Y0) // 5
DEF = {'footway': 2.8, 'path': 1.5, 'steps': 2.5, 'cycleway': 3, 'service': 6, 'pedestrian': 5, 'living_street': 5}
BB = box(XA - 50, YA - 50, XB + 50, YB + 50)
# 공원 안 큰 차도(카카오맵의 넓은 흰 길: 돔 동쪽에서 한얼광장 지나 남서쪽): 걸어 다니는 길로 칠하지 않음
CARROAD = {'688650627'}
poly = lambda r: Polygon(r['xy']) if len(r['xy']) >= 3 and r['xy'][0] == r['xy'][-1] else None
geo, added = [], []
for r in R:
    if r['kind'] == 'H':
        hw = osm.tagval(r['raw'], 'highway'); g = LineString(r['xy'])
        if hw not in DEF or not g.intersects(BB) or r['id'] in CARROAD: continue
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
# 4·5 사람이 지나갈 수 없는 곳(빨강): osm_dome.txt(2026-11-28 Overpass, 이 구역) 기준. 걸을 수 있는 칸·건물·주차장은 빼고 칸 면적 5㎡ 이상
import osm_dome
from shapely.geometry import Point
RD = osm_dome.load(); BLOCK, ROAD = [], []
INDOOR = {'470689431', '470689432', '683545632', '75956847'}  # 실내 수영장·체육과학관·실내테니스장: 건물이라 빨강에서 뺌(OSM에 building 태그가 없을 뿐)
CAR_SERVICE_OK = {'923609912', '923609913', '923609914', '923609915', '923609916', '239951038', '688650626', '1321739839'}  # 걸어 다니는 통로·정문 다리·주차장 통로
for r in RD:
    t = r['tags']; xy = r['xy']
    if len(xy) < 2: continue
    hw = t.get('highway')
    if t.get('foot') == 'no': BLOCK.append(LineString(xy).buffer(1.5, cap_style=2))                                   # 자전거 전용(사람 금지) 길·다리
    elif hw == 'primary': BLOCK.append(LineString(xy).buffer(float(t.get('lanes', 6)) * 3.25 / 2, cap_style=2))     # 양재대로·오륜교(12차로)
    elif t.get('leisure') in ('pitch', 'swimming_pool') and xy[0] == xy[-1] and r['id'] not in INDOOR: BLOCK.append(Polygon(xy).buffer(0))     # 울타리 친 경기장·수영장
    elif hw == 'residential': ROAD.append(LineString(xy).buffer(4, cap_style=2))
    elif hw == 'service' and r['id'] not in CAR_SERVICE_OK: ROAD.append(LineString(xy).buffer(4, cap_style=2))      # 차도(건널목·육교로만 건넘), 폭 8m 가정
NOPAINT = shapely.union_all([Polygon(r['xy']).buffer(0) for r in RD if ('building' in r['tags'] or r['tags'].get('amenity') == 'parking') and len(r['xy']) > 3 and r['xy'][0] == r['xy'][-1]] + [EXC])
BL = shapely.union_all(BLOCK).difference(NOPAINT); RO = shapely.union_all(ROAD).difference(NOPAINT).difference(BL)
aB = shapely.area(shapely.intersection(cells, BL)); aR = shapely.area(shapely.intersection(cells, RO))
for k in range(len(ii)):
    i, j = ii[k], jj[k]
    if 21 <= L[j, i] <= 25 and aR[k] >= 12.5: L[j, i] = 51; continue   # 사진 포장면이 차도 위(칸 절반 이상)면 차도로
    if L[j, i]: continue
    if aB[k] >= 5: L[j, i] = 41
    elif aR[k] >= 5: L[j, i] = 51
print('빨강 못 지나감', int((L == 41).sum()), '칸 · 차도(건널목으로만)', int((L == 51).sum()), '칸')
# 6 사람이 넘을 수 없는 울타리·난간(빨간 선, 칸이 아니라 선). 있는지는 카카오 로드뷰로 눈으로만 확인(따라 그리지 않음),
#   위치는 OSM 중심선에서 위성(Esri World Imagery, z19)으로 잰 차도 가장자리까지 옮겨 그림. 좌표는 (967000, 1946600) 기준 m
from shapely.ops import substring
OX, OY = 967000, 1946600
def wy(i): return LineString(next(r for r in RD if r['id'] == i)['xy'])
def part(g, a, b): return substring(g, g.project(Point(OX + a[0], OY + a[1])), g.project(Point(OX + b[0], OY + b[1])))
rd, st = wy('239950534'), wy('239951575')
BAR = [
  ('돔 동쪽 차도 동쪽 차량 방호 울타리(뒤는 성내천 쪽 급경사)', '2026-06', part(rd, (170, 12), (152, 252)).offset_curve(-8.4)),
  ('돔 동쪽 차도 서쪽 생울타리(남쪽 구간)', '2026-06', part(rd, (175, 30), (189, 98)).offset_curve(6.1)),
  ('돔 동쪽 차도 서쪽 생울타리(북쪽 구간)', '2026-06', part(rd, (189, 108), (158, 238)).offset_curve(6.1)),
]
band = rd.buffer(8.4)
for i, other in (('923609908', '923609910'), ('923609910', '923609908')):    # 한얼다리 양쪽 난간: 다리 가장자리 중 차도 위 부분
    g, o = wy(i), wy(other); cand = [g.offset_curve(d) for d in (1.5, -1.5)]; e = max(cand, key=lambda c: c.distance(o))
    BAR.append(('한얼다리 난간(아래는 차도)', '2008·2015', e.intersection(band.buffer(2))))
BAR.append(('올림픽공원역 앞 상가 보도와 차도 사이 난간', '2015-09', part(st, (228, -180), (317, -228)).offset_curve(7)))
for nm, d, g in BAR: assert g.length > 5, nm
# 넘을 수 없는 선을 가로지르는 칸 사이 이동은 막고 돔에서 다시 이어 봄(칸은 지우지 않고 세기만)
BU = shapely.union_all([g for _, _, g in BAR]); near = BU.buffer(8)
walk = (L >= 11) & (L <= 35); reach = np.zeros_like(walk); stk = [s for s in seed if walk[s]]
for s in stk: reach[s] = True
cut = 0
while stk:
    j, i = stk.pop(); cx, cy = X0 + i * 5 + 2.5, Y0 + j * 5 + 2.5; nb = near.contains(Point(cx, cy))
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            a, b = j + dj, i + di
            if (dj or di) and 0 <= a < H and 0 <= b < W and walk[a, b] and not reach[a, b]:
                if nb and LineString([(cx, cy), (cx + di * 5, cy + dj * 5)]).intersects(BU): cut += 1; continue
                reach[a, b] = True; stk.append((a, b))
print('넘을 수 없는 선', len(BAR), '개, 길이', {nm: round(g.length) for nm, _, g in BAR}, '| 선에 막힌 칸 사이 이동', cut, '| 선 때문에 돔에서 못 가게 된 걷는 칸', int((walk & ~reach).sum()))
# 선 때문에 돔에서 못 가게 된 칸은 이 층의 정의(돔과 이어진 길)에서 뺌: 위성으로 잰 차도 폭(돔 동쪽 차도 약 14m, 역 앞 차도 약 14m) 안이면 차도로, 아니면 비움
RB = shapely.union_all([rd.buffer(8.4), st.buffer(7)]); moved = {}
for j, i in zip(*np.where(walk & ~reach)):
    v = 51 if RB.contains(Point(X0 + i * 5 + 2.5, Y0 + j * 5 + 2.5)) else 0; moved[(int(L[j, i]) // 10, v)] = moved.get((int(L[j, i]) // 10, v), 0) + 1; L[j, i] = v
print('선 때문에 옮긴 칸 (원래 종류, 옮긴 값):', moved)
import json
json.dump([[nm, d, [[[round(x, 1), round(y, 1)] for x, y in ls.coords] for ls in (getattr(g, 'geoms', None) or [g])]] for nm, d, g in BAR], open('dome_barriers.json', 'w'), ensure_ascii=False)
np.save('dome_layer.npy', L)
c = zlib.compressobj(9, zlib.DEFLATED, -15); b = c.compress(L.tobytes()) + c.flush(); open('dome_layer.b64', 'w').write(base64.urlsafe_b64encode(b).decode().rstrip('='))
mid = {1: 2.5, 2: 7.5, 3: 12.5, 4: 17.5, 5: 22.5}
for cat, nm in ((1, '기존'), (2, '사진 포장(확인 필요였던 곳)'), (3, '새로 칠한 길')):
    m = (L // 10) == cat; print(nm, int(m.sum()), '칸, 보행 면적 약', round(sum(mid[int(x) % 10] for x in L[m])), '㎡')
print('돔 둘레 출발 칸', len(seed), '| 구역 안 칠한 칸 전체', int((L > 0).sum()), '| 이어지지 않아 뺀 칸', int(((L == 0) & False).sum()))
# 새로 칠한 길에 들어간 OSM 길(차량 통로)
print([a for a in added if a[1] in ('service', 'living_street') and a[3] > 0])
