"""주말·공연 날 전용 사람 수 모델을 2025년 자료로 만들고 채점해요(공원 = 서울시 '올림픽공원' 영역 생활인구, 시간별).
사용: data 폴더에서 python3 ../analysis/showmodel.py  (~/past3.pkl, checks/park_population_2025_hourly_poi127_full.csv, weather_asos_108_2025.csv)
예측하는 값: 그날 새벽(2~4시) 값 + 시간별 늘어나는 폭. 채점: 7~23시, 정확도 = 100×(1−Σ|오차|÷Σ실제).
모델
  M0 사이트 지금: 7종류(월~목, 금, 토, 일·공휴일 × 큰 공연 있음/없음)별 시계 시각 중앙값. 평일 공휴일은 월~목으로 봄(사이트와 같음)
  M1 날 종류 바로잡기: M0에서 평일 공휴일·명절을 따로 두고, 공연 날은 '공연 시작 시각 기준' 중앙값(공연장·요일별)
  M2 나눠 더하기(릿지 회귀): 날 종류×시각 + 계절(1년 주기 곡선)×주말×시간대 + 날씨(비·기온) + 공연장별(KSPO DOME, 핸드볼경기장, 올림픽홀, 88잔디마당) '시작 시각 기준 모양'(평일·주말 따로)
  M3 M2 + 최근 날 보정: 같은 달에서 이미 지난 같은 종류(평일/주말) 날들의 낮 시간 오차 중앙값을 더함(실시간 기록으로 하는 것과 같은 일)
  M4 그래디언트 부스팅: M2와 같은 재료로 나무 모델
채점 방식: (가) 한 달씩 빼고 나머지 11달로 배움, (나) 지난 달들만으로 배움(3~12월, 실제 쓰는 상황)
날씨는 실제 관측값을 예보 대신 썼어요(예보 오차만큼 실제보다 좋게 나올 수 있음)."""
import os, pickle, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
P = pickle.load(open(os.path.expanduser('~/past3.pkl'), 'rb')); G, SHOW = P['G'], P['show']
PO = pd.read_csv('checks/park_population_2025_hourly_poi127_full.csv'); PO['ts'] = pd.to_datetime(PO.ts); PO['d'] = PO.ts.dt.strftime('%Y-%m-%d'); PO['h'] = PO.ts.dt.hour
Y = PO.pivot_table(index='d', columns='h', values='park_pop'); days = list(Y.index); DAWN = Y[[2, 3, 4]].median(axis=1); INC = Y.sub(DAWN, axis=0)
Wx = pd.read_csv('weather_asos_108_2025.csv', encoding='utf-8-sig', usecols=['tm', 'ta', 'rn']); Wx['ts'] = pd.to_datetime(Wx.tm); Wx['d'] = Wx.ts.dt.strftime('%Y-%m-%d'); Wx['h'] = Wx.ts.dt.hour
RN = Wx.pivot_table(index='d', columns='h', values='rn').reindex(days).fillna(0); TA = Wx.pivot_table(index='d', columns='h', values='ta').reindex(days).interpolate(axis=1, limit_direction='both').fillna(10)
wd = {d: pd.Timestamp(d).weekday() for d in days}
def base(d):
    g = G.get(d, '')
    if g == '명절': return '명절'
    if g.startswith('평일 공휴일'): return '평일공휴일'
    return '월~목' if wd[d] < 4 else '금' if wd[d] == 4 else '토' if wd[d] == 5 else '일'
BASE = {d: base(d) for d in days}; wkend = lambda d: BASE[d] in ('토', '일', '평일공휴일', '명절')
TIERS = ('big', 'mid', 'small', 'fest')
def starts(d): return {t: min(int(s['t'][:2]) + int(s['t'][3:5]) / 60 for s in SHOW[d][t]) for t in TIERS if t in SHOW.get(d, {})}
ST = {d: starts(d) for d in days}
def grp(d):
    b = BASE[d]; s = ST[d]
    if b in ('명절',): return '설·추석 연휴'
    if b == '평일공휴일': return '평일 공휴일'
    if 'fest' in s: return '야외 축제'
    if 'big' in s: return {'월~목': '월~목 큰 공연', '금': '금 큰 공연', '토': '토 큰 공연', '일': '일 큰 공연'}[b]
    if 'mid' in s or 'small' in s: return ('주말' if b in ('토', '일') else '평일') + ' 중간·작은 공연'
    return {'월~목': '월~목 공연 없음', '금': '금 공연 없음', '토': '토 공연 없음', '일': '일 공연 없음'}[b]
GRP = {d: grp(d) for d in days}
# ---------- M0 / M1
def m0_cls(d):
    b = wd[d]; big = 'big' in ST[d]
    if b < 4: return 'wk'
    k = 'fri' if b == 4 else 'sat' if b == 5 else 'hol'
    if G.get(d, '').startswith('평일 공휴일') and not big: k = 'wk'
    return k + ('_show' if big else '')
def fit_m0(train):
    C = {}
    for d in train: C.setdefault(m0_cls(d), []).append(INC.loc[d].values)
    return {k: np.median(v, axis=0) for k, v in C.items()}
def pred_m0(M, d): return M.get(m0_cls(d), M['wk'])
def m1_key(d):
    s = ST[d]; b = BASE[d]
    tier = next((t for t in TIERS if t in s), None)
    side = 'we' if b in ('토', '일', '평일공휴일') else 'wd'
    return (tier, side, b if tier is None else ('금' if b == '금' else side))
def fit_m1(train):
    clock, rel = {}, {}
    for d in train:
        k = m1_key(d); clock.setdefault(('all', BASE[d]), []).append(INC.loc[d].values)
        if not ST[d]: clock.setdefault(('none', BASE[d]), []).append(INC.loc[d].values)
        if k[0]:
            st = int(ST[d][k[0]])
            for h in range(24): rel.setdefault((k[0], k[2]), {}).setdefault(h - st, []).append(INC.loc[d, h])
    C = {k: np.median(v, axis=0) for k, v in clock.items() if len(v) >= 5 or k[0] == 'all'}
    return C, {k: {r: np.median(x) for r, x in v.items() if len(x) >= 3} for k, v in rel.items()}
def pred_m1(M, d):
    clock, rel = M; k = m1_key(d); b = BASE[d]
    p = (clock.get(('none', b)) if ('none', b) in clock else clock.get(('all', b), clock[('all', '월~목')])).copy()
    if k[0] and (k[0], k[2]) in rel:
        st = int(ST[d][k[0]]); R = rel[(k[0], k[2])]
        for h in range(24):
            if (h - st) in R: p[h] = R[h - st]
    return p
# ---------- M2 (릿지)
BASES = ['월~목', '금', '토', '일', '평일공휴일', '명절']; RELS = list(range(-6, 7))
def feats(d):
    X = []; b = BASE[d]; m = int(d[5:7]); we = 1 if wkend(d) else 0
    for h in range(24):
        f = {}
        f['b_%s_%d' % (b, h)] = 1; doy = pd.Timestamp(d).dayofyear; f['sc_%d_%d' % (we, h // 4)] = np.cos(2 * np.pi * doy / 365); f['ss_%d_%d' % (we, h // 4)] = np.sin(2 * np.pi * doy / 365)
        r = RN.loc[d, h]; t = TA.loc[d, h]; day = 1 if 9 <= h <= 21 else 0
        f['rain_%d_%d' % (we, day)] = min(r, 10); f['rainy_%d_%d' % (we, day)] = 1 if r > 0.2 else 0
        f['ta_%d_%d' % (we, day)] = (t - 15) / 10; f['ta2_%d_%d' % (we, day)] = ((t - 15) / 10) ** 2
        for tier, s in ST[d].items():
            rr = h - int(s)
            if rr in RELS: f['s_%s_%d_%d' % (tier, we, rr)] = 1
        X.append(f)
    return X
FE = {d: feats(d) for d in days}
def design(ds, cols=None):
    rows = [f for d in ds for f in FE[d]]
    if cols is None: cols = sorted({k for f in rows for k in f})
    ix = {c: i for i, c in enumerate(cols)}; A = np.zeros((len(rows), len(cols)))
    for i, f in enumerate(rows):
        for k, v in f.items():
            if k in ix: A[i, ix[k]] = v
    return A, cols
def fit_m2(train, alpha=3.0):
    A, cols = design(train); y = np.concatenate([INC.loc[d].values for d in train])
    beta = np.linalg.solve(A.T @ A + alpha * np.eye(A.shape[1]), A.T @ y); return beta, cols
def pred_m2(M, ds):
    beta, cols = M; A, _ = design(ds, cols); return (A @ beta).reshape(len(ds), 24)
def fit_m4(train):
    from sklearn.ensemble import HistGradientBoostingRegressor
    A, cols = design(train); y = np.concatenate([INC.loc[d].values for d in train])
    g = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06, max_leaf_nodes=31, l2_regularization=1.0, random_state=0).fit(A, y); return g, cols
def pred_m4(M, ds):
    g, cols = M; A, _ = design(ds, cols); return g.predict(A).reshape(len(ds), 24)
def recent_fix(pred, test):
    out = pred.copy(); E = {}
    for i, d in enumerate(test):
        prev = [x for x in E if x < d and wkend(x) == wkend(d) and (pd.Timestamp(d) - pd.Timestamp(x)).days <= 21][-3:]
        if len(prev) >= 1: out[i, 9:22] += np.median([E[x] for x in prev], axis=0)
        E[d] = (INC.loc[d].values - pred[i])[9:22]
    return out
SEQ = {d: SHOW[d]['big'][0].get('seq') for d in days if 'big' in SHOW.get(d, {})}
def prev_run(d):
    s = SEQ.get(d)
    if s is None: return None
    c = [x for x in days if x < d and SEQ.get(x) == s and (pd.Timestamp(d) - pd.Timestamp(x)).days <= 3]
    return c[-1] if c else None
def carry(pred, test, alpha):
    out = {d: pred[d].copy() for d in test}
    for d in test:
        p = prev_run(d)
        if p is None or p not in pred: continue
        r = INC.loc[p].values - pred[p]; sp = int(ST[p]['big']); sd = int(ST[d]['big'])
        for rel in range(-6, 6):
            if 0 <= sp + rel < 24 and 0 <= sd + rel < 24: out[d][sd + rel] += alpha * r[sp + rel]
    return out
def run(split):
    PR = {k: {} for k in ('M0 사이트 지금', 'M1 날 종류·시작 시각', 'M2 나눠 더하기', 'M3 M2+최근 날 보정', 'M4 부스팅')}
    months = range(1, 13) if split == 'lomo' else range(3, 13)
    for m in months:
        test = [d for d in days if int(d[5:7]) == m]
        train = [d for d in days if int(d[5:7]) != m] if split == 'lomo' else [d for d in days if int(d[5:7]) < m]
        M0 = fit_m0(train); M1 = fit_m1(train); M2 = fit_m2(train); M4 = fit_m4(train)
        p2 = pred_m2(M2, test); p3 = recent_fix(p2, test); p4 = pred_m4(M4, test)
        for i, d in enumerate(test):
            PR['M0 사이트 지금'][d] = pred_m0(M0, d); PR['M1 날 종류·시작 시각'][d] = pred_m1(M1, d)
            PR['M2 나눠 더하기'][d] = p2[i]; PR['M3 M2+최근 날 보정'][d] = p3[i]; PR['M4 부스팅'][d] = p4[i]
    for k, a in (('M0 사이트 지금', 0.8), ('M1 날 종류·시작 시각', 0.8), ('M3 M2+최근 날 보정', 0.8)):
        PR[k[:2] + '+같은 공연 전날'] = carry(PR[k], list(PR[k]), a)
    return PR
ORDER = ['둘째 날 이후 큰 공연', '월~목 공연 없음', '금 공연 없음', '금 큰 공연', '토 큰 공연', '일 큰 공연', '주말 중간·작은 공연', '평일 중간·작은 공연', '월~목 큰 공연', '평일 공휴일', '설·추석 연휴', '야외 축제']
H = list(range(7, 24)); OUT = {}
for split, lab in (('lomo', '(가) 한 달씩 빼고 배움'), ('roll', '(나) 지난 달들만으로 배움, 3~12월')):
    PR = run(split); print('\n== %s. 칸 = 정확도%%(시간당 평균 오차 명)' % lab)
    print('%-18s %4s | ' % ('날 종류', '일수') + ' | '.join('%-13s' % k[:13] for k in PR))
    res = {}
    for g in ORDER + ['주말·공연·공휴일 전체', '전체']:
        ds = [d for d in PR['M0 사이트 지금'] if (GRP[d] == g or (g == '전체') or (g == '주말·공연·공휴일 전체' and GRP[d] not in ('월~목 공연 없음', '금 공연 없음')) or (g == '둘째 날 이후 큰 공연' and prev_run(d) is not None))]
        if not ds: continue
        line = '%-18s %4d | ' % (g, len(ds)); res[g] = {}
        for k, pr in PR.items():
            e = np.concatenate([np.abs((DAWN[d] + pr[d][H]) - Y.loc[d, H].values) for d in ds]); a = np.concatenate([Y.loc[d, H].values for d in ds])
            acc = 100 * (1 - e.sum() / a.sum()); res[g][k] = (round(acc, 1), round(float(e.mean())))
            line += '%5.1f%%(%5.0f) | ' % (acc, e.mean())
        print(line)
    OUT[split] = res
json.dump(OUT, open('checks/showmodel_2025.json', 'w'), ensure_ascii=False)
