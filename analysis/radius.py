"""올림픽공원역 → KSPO DOME 반경만 떼어 보면 첫날 공연을 더 잘 맞히는지 2025년 250m 생활인구로 봐요.
사용: data 폴더에서 python3 ../analysis/radius.py ../analysis/kopis_daily_2025.csv
필요: livingpop_grid/2025MM.csv(250m 칸, 시간별), checks/poi127_overlap.json(칸이 서울시 '올림픽공원' 영역과 겹치는 몫),
      checks/park_population_2025_hourly_poi127_full.csv(맞는지 확인용), ~/past3.pkl(날짜 종류·공연)
구역: 역(올림픽공원역 출구)에서 KSPO DOME 칸 가운데까지 선분에서 r m 안에 가운데가 있는 칸(r = 0이면 DOME 칸만)
채점: KSPO DOME 공연 날, 지난 달들만으로 배움(3~12월), 07~23시, 정확도 = 100×(1−Σ|오차|÷Σ실제)
  (가) 구역 자체를 맞히기: 날 종류 중앙값(M0) / 시작 시각 맞춤(A) / 판매수 크기(T, 공연 뒤에야 아는 값) / A+같은 공연 전날
  (나) 공원 전체 = 구역 몫 + 나머지로 나눠 맞히기: 구역은 A, 나머지는 날 종류 중앙값 → 지금 사이트(M0, 공원 전체 한 덩어리)와 비교"""
import os, sys, glob, json, math, pickle, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
P = pickle.load(open(os.path.expanduser('~/past3.pkl'), 'rb')); G, SHOW = P['G'], P['show']
FRAC = json.load(open('checks/poi127_overlap.json', encoding='utf-8'))['frac']
ZC = json.load(open('checks/zone_cells_2025.json', encoding='utf-8'))
CACHE = os.path.expanduser('~/cells_2025.pkl')
if os.path.exists(CACHE): C = pd.read_pickle(CACHE)
else:
    need = set(ZC) | {c for c, f in FRAC.items() if f > 0}; fr = []
    for f in sorted(glob.glob('livingpop_grid/2025??.csv')):
        d = pd.read_csv(f, dtype=str, encoding='utf-8-sig', usecols=['date', 'hour', 'cell', 'total']); d['c'] = d.cell.str[-8:]; d = d[d.c.isin(need)]
        d['v'] = pd.to_numeric(d.total, errors='coerce').fillna(0); fr.append(d[['date', 'hour', 'c', 'v']])
    C = pd.concat(fr); C['d'] = pd.to_datetime(C.date).dt.strftime('%Y-%m-%d'); C['h'] = C.hour.astype(int)
    C = C.pivot_table(index=['d', 'h'], columns='c', values='v', aggfunc='sum').fillna(0); C.to_pickle(CACHE)
def inv(E, N):
    a = 6378137.0; f = 1 / 298.257222101; k0 = 0.9996; lat0 = math.radians(38); lon0 = math.radians(127.5); FE = 1e6; FN = 2e6
    e2 = 2 * f - f * f; ep2 = e2 / (1 - e2)
    def M(p): return a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * p - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * p) + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * p) - (35 * e2 ** 3 / 3072) * math.sin(6 * p))
    M1 = M(lat0) + (N - FN) / k0; mu = M1 / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256)); e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    p1 = mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu) + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
    C1 = ep2 * math.cos(p1) ** 2; T1 = math.tan(p1) ** 2; N1 = a / math.sqrt(1 - e2 * math.sin(p1) ** 2); R1 = a * (1 - e2) / (1 - e2 * math.sin(p1) ** 2) ** 1.5; D_ = (E - FE) / (N1 * k0)
    lat = p1 - (N1 * math.tan(p1) / R1) * (D_ * D_ / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 * C1 - 9 * ep2) * D_ ** 4 / 24)
    return math.degrees(lat), math.degrees(lon0 + (D_ - (1 + 2 * T1 + C1) * D_ ** 3 / 6) / math.cos(p1))
LL = {c: inv(900000 + int(c[:4]) * 10 + 125, 1900000 + int(c[4:]) * 10 + 125) for c in C.columns}
xy = lambda la, lo: np.array((lo * 88200, la * 110900))
STN, DOMEC = (37.516235, 127.130605), LL['67004650']
def seg_d(p):
    P_, A, B = xy(*p), xy(*STN), xy(*DOMEC); t = np.clip(np.dot(P_ - A, B - A) / np.dot(B - A, B - A), 0, 1); return float(np.linalg.norm(P_ - (A + t * (B - A))))
# 맞는지: 겹치는 몫으로 더한 값 = 공원 전체 시계열
fr_ = pd.Series({c: FRAC.get(c, 0) for c in C.columns}); TOT = (C * fr_).sum(axis=1).unstack('h')
PO = pd.read_csv('checks/park_population_2025_hourly_poi127_full.csv'); PO['ts'] = pd.to_datetime(PO.ts); PO['d'] = PO.ts.dt.strftime('%Y-%m-%d'); PO['h'] = PO.ts.dt.hour
Y0 = PO.pivot_table(index='d', columns='h', values='park_pop'); days = [d for d in Y0.index if d in TOT.index]
print('확인: 칸을 더한 공원 전체와 저장해 둔 공원 전체의 차이 최대 %.1f명' % float(np.nanmax(np.abs(TOT.loc[days].values - Y0.loc[days].values))))
K = pd.read_csv(sys.argv[1] if len(sys.argv) > 1 else '../analysis/kopis_daily_2025.csv', dtype={'from': str}); K['d'] = pd.to_datetime(K['from']).dt.strftime('%Y-%m-%d')
TK = K[K.prfnmplc.str.startswith('KSPO DOME') & (K.totnmrs > 0)].set_index('d').totnmrs
wd = {d: pd.Timestamp(d).weekday() for d in days}
def base(d):
    g = G.get(d, '')
    if g == '명절': return '명절'
    if g.startswith('평일 공휴일'): return '평일공휴일'
    return '월~목' if wd[d] < 4 else '금' if wd[d] == 4 else '토' if wd[d] == 5 else '일'
BASE = {d: base(d) for d in days}; side = lambda d: 'we' if BASE[d] in ('토', '일', '평일공휴일', '명절') else 'wd'
ST = {d: min(int(s['t'][:2]) + int(s['t'][3:5]) / 60 for s in SHOW[d]['big']) for d in days if 'big' in SHOW.get(d, {})}
NSH = {d: len(SHOW[d]['big']) for d in ST}; SEQ = {d: SHOW[d]['big'][0].get('seq') for d in ST}
def prev_run(d):
    c = [x for x in days if x < d and SEQ.get(x) == SEQ.get(d) and SEQ.get(d) is not None and (pd.Timestamp(d) - pd.Timestamp(x)).days <= 3]
    return c[-1] if c else None
def m0_cls(d):
    b = wd[d]; big = d in ST
    if b < 4: return 'wk'
    k = 'fri' if b == 4 else 'sat' if b == 5 else 'hol'
    if G.get(d, '').startswith('평일 공휴일') and not big: k = 'wk'
    return k + ('_show' if big else '')
H = list(range(7, 24)); RELS = range(-8, 7)
def W(d, a=-3, b=4): return [h for h in range(int(ST[d]) + a, int(ST[d]) + b) if 0 <= h < 24]
def models(Y):
    DAWN = Y[[2, 3, 4]].median(axis=1); INC = Y.sub(DAWN, axis=0); PR = {k: {} for k in ('M0', 'A', 'T')}
    for m in range(3, 13):
        test = [d for d in days if int(d[5:7]) == m and d in ST]; train = [d for d in days if int(d[5:7]) < m]
        Cm = {}
        for d in train: Cm.setdefault(m0_cls(d), []).append(INC.loc[d].values)
        M0 = {k: np.median(v, axis=0) for k, v in Cm.items()}
        NB, ALLB = {}, {}
        for d in train:
            ALLB.setdefault(BASE[d], []).append(INC.loc[d].values)
            if d not in ST: NB.setdefault(BASE[d], []).append(INC.loc[d].values)
        NB = {k: np.median(v, axis=0) for k, v in NB.items() if len(v) >= 3}
        def nb(d):
            for k in (BASE[d], '일' if side(d) == 'we' else '월~목', '토' if side(d) == 'we' else '금'):
                if k in NB: return NB[k]
            return np.median(ALLB.get(BASE[d], ALLB['월~목']), axis=0)
        avg, per = {}, {}
        for d in train:
            if d not in ST or NSH[d] != 1: continue
            st = int(ST[d]); ex = INC.loc[d].values - nb(d)
            for r in RELS:
                if 0 <= st + r < 24:
                    avg.setdefault((side(d), r), []).append(ex[st + r])
                    if d in TK: per.setdefault((side(d), r), []).append(ex[st + r] / TK[d])
        AVG = {k: np.median(v) for k, v in avg.items() if len(v) >= 3}; PER = {k: np.median(v) for k, v in per.items() if len(v) >= 3}
        def shaped(tab, d, s=1.0):
            p = nb(d).copy(); st = int(ST[d])
            for r in RELS:
                if 0 <= st + r < 24 and (side(d), r) in tab: p[st + r] += s * tab[(side(d), r)]
            return p
        for d in test:
            PR['M0'][d] = M0.get(m0_cls(d), M0['wk']); PR['A'][d] = shaped(AVG, d); PR['T'][d] = shaped(PER, d, TK[d]) if d in TK else PR['A'][d]
    out = {d: v.copy() for d, v in PR['A'].items()}
    for d in out:
        p = prev_run(d)
        if p is None or p not in PR['A']: continue
        r = INC.loc[p].values - PR['A'][p]; sp, sd = int(ST[p]), int(ST[d])
        for rel in range(-6, 6):
            if 0 <= sp + rel < 24 and 0 <= sd + rel < 24: out[d][sd + rel] += 0.8 * r[sp + rel]
    PR['A+전날'] = out
    return PR, DAWN, INC
def acc(Y, DAWN, pr, ds, win=False):
    e, a = [], []
    for d in ds:
        hs = [h for h in range(int(ST[d]) - 3, int(ST[d]) + 4) if 7 <= h <= 23] if win else H
        e.append(np.abs(DAWN[d] + pr[d][hs] - Y.loc[d, hs].values)); a.append(Y.loc[d, hs].values)
    e, a = np.concatenate(e), np.concatenate(a); return 100 * (1 - e.sum() / a.sum()), e.mean()
ALLD = sorted(d for d in ST if int(d[5:7]) >= 3); FIRST = [d for d in ALLD if prev_run(d) is None]; LATER = [d for d in ALLD if prev_run(d) is not None]
print('\n== (가) 구역 자체를 맞히기 (KSPO DOME 공연 날: 첫날 %d일, 둘째 날 이후 %d일)' % (len(FIRST), len(LATER)))
print('  %-24s %5s %8s | %-15s %-15s %-15s %-15s | %-13s | %s' % ('구역', '칸 수', '공연 몫', 'M0 날 종류', 'A 시작 시각', 'T 판매수(사후)', 'A+같은 공연 전날', '첫날 공연앞뒤 A', '판매수 상관(첫날)'))
ZONES = {}
for r in (0, 150, 300, 450, 600):
    cs = [c for c in C.columns if c == '67004650' or (r > 0 and seg_d(LL[c]) <= r)]
    ZONES[r] = cs; Y = C[cs].sum(axis=1).unstack('h').loc[days]; PR, DAWN, INC = models(Y)
    shr = np.mean([np.mean(INC.loc[d, W(d)].values) for d in FIRST])
    cells = []
    for k in ('M0', 'A', 'T', 'A+전날'):
        cells.append('%5.1f%% / %5.1f%%' % (acc(Y, DAWN, PR[k], FIRST)[0], acc(Y, DAWN, PR[k], LATER)[0]))
    ex = [(TK[d], np.mean(INC.loc[d, W(d, -2, 2)].values)) for d in FIRST if d in TK and NSH[d] == 1]
    ex = np.array(ex); rr = np.corrcoef(ex[:, 0], ex[:, 1])[0, 1]
    print('  r=%3dm (%-15s) %4d %7.0f명 | %s | %5.1f%%        | %.2f' % (r, 'DOME 칸만' if r == 0 else '역~돔 선분 둘레', len(cs), shr, ' | '.join('%-15s' % c for c in cells), acc(Y, DAWN, PR['A'], FIRST, True)[0], rr))
print('  (칸마다 "첫날 / 둘째 날 이후" 정확도. 공연 몫 = 첫날 공연 앞뒤 3시간 평균 새벽 대비 증가)')
for r, cs in ZONES.items(): print('   r=%dm 칸: %s' % (r, ', '.join('%s(%s, 밤 %d명)' % (c, ZC.get(c, {}).get('z', '바깥'), ZC.get(c, {}).get('night', -1)) for c in cs)))
print('\n== (나) 공원 전체를 "구역 몫 + 나머지"로 나눠 맞히기 (서울시 올림픽공원 영역과 겹치는 몫으로 더함)')
YT = TOT.loc[days]; PRT, DT, _ = models(YT)
print('  지금 사이트(M0, 한 덩어리): 첫날 %.1f%%, 둘째 날 이후 %.1f%% | 시작 시각 맞춤(A, 한 덩어리): 첫날 %.1f%%' % (acc(YT, DT, PRT['M0'], FIRST)[0], acc(YT, DT, PRT['M0'], LATER)[0], acc(YT, DT, PRT['A'], FIRST)[0]))
for r in (0, 150, 300, 450, 600):
    cs = ZONES[r]; w = pd.Series({c: FRAC.get(c, 0) for c in C.columns})
    YZ = (C[cs] * w[cs]).sum(axis=1).unstack('h').loc[days]; YR = YT - YZ
    PZ, DZ, _ = models(YZ); PRr, DR, _ = models(YR)
    S = {d: PZ['A'][d] + PRr['M0'][d] for d in ALLD}; DS = DZ + DR
    eZ = sum(np.abs(DZ[d] + PZ['A'][d][H] - YZ.loc[d, H].values).sum() for d in FIRST); eR = sum(np.abs(DR[d] + PRr['M0'][d][H] - YR.loc[d, H].values).sum() for d in FIRST)
    print('  r=%3dm: 나눠 맞히기 첫날 %.1f%%, 둘째 날 이후 %.1f%% | 첫날 오차 중 구역 몫 %2.0f%%, 나머지 몫 %2.0f%% | 구역이 공원 전체 첫날 공연 몫에서 차지하는 비율 %2.0f%%' % (
        r, acc(YT, DS, S, FIRST)[0], acc(YT, DS, S, LATER)[0], 100 * eZ / (eZ + eR), 100 * eR / (eZ + eR),
        100 * np.mean([np.mean(YZ.loc[d, W(d)].values - DZ[d]) for d in FIRST]) / np.mean([np.mean(YT.loc[d, W(d)].values - DT[d]) for d in FIRST])))
