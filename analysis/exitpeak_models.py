"""공연 뒤 '출차 혼잡' 시점(혼잡 시작·최대·끝)을 여러 모델로 예측하고 2025 KSPO DOME 저녁으로 하루씩(같은 투어 통째로) 빼고 검증.
정답(2025): 공연 시작 뒤 10분 순유출(나간 차 − 들어온 차, 2025 단위)이 120대 이상인 칸(시작+60분 이후). 2026은 × 0.649 = 78대.
"""
import os, sys, json, pickle, calendar, numpy as np, pandas as pd
D = sys.argv[1]; os.chdir(D)
P = pickle.load(open(os.path.expanduser('~/past3.pkl'), 'rb')); SHOW = P['show']
HOL = {r[:4] + '-' + r[4:6] + '-' + r[6:] for r in pd.read_csv('holidays.csv', dtype=str).iloc[:, 0]}
wkg = lambda d: 1 if pd.Timestamp(d).weekday() >= 5 or d in HOL else 0
hm = lambda t: int(t[:2]) * 60 + int(t[3:5])
E = json.load(open('checks/end_detect_2025.json')); EV = E['1~6월(정할 때 쓴 저녁)']['evenings'] + E['7·10·11월(채점)']['evenings']
df = pd.read_csv('inout_2025_full.csv', usecols=['entry_gate', 'entry_time', 'exit_time'], encoding='utf-8-sig'); df = df[~df.entry_gate.str.contains('CMB')]
en = pd.to_datetime(df.entry_time, errors='coerce').dropna(); ex = pd.to_datetime(df.exit_time, errors='coerce').dropna()
B5 = lambda s: s.dt.floor('5min').value_counts()
NET = (B5(ex).sub(B5(en), fill_value=0)).sort_index()
bad = lambda d: d[5:7] in ('08', '09') or (d[5:7] == '11' and int(d[8:]) > 6) or (d[5:7] == '12' and int(d[8:]) > 7) or int(d[8:]) == calendar.monthrange(int(d[:4]), int(d[5:7]))[1]
dome = lambda d: [b for b in SHOW.get(d, {}).get('big', []) if 'KSPO' in b['venue']]
def series10(d, st):
    idx = pd.date_range(pd.Timestamp(d) + pd.Timedelta(minutes=st), periods=72, freq='5min'); s = NET.reindex(idx).fillna(0).values
    return s.reshape(-1, 2).sum(1)  # 36칸 = 시작 뒤 0~360분
THR = 120.0; I0 = 6
ROWS = []
for e in EV:
    d = e['d']; b = dome(d)
    if len(b) != 1 or bad(d): continue
    st = hm(b[0]['t']); run = b[0].get('run'); run = float(run) if run == run and run is not None else np.nan
    s = series10(d, st); busy = [i for i in range(I0, 36) if s[i] >= THR]
    other = len([x for x in SHOW.get(d, {}).get('big', []) + SHOW.get(d, {}).get('small', []) if 'KSPO' not in x['venue'] and hm(x['t']) >= st - 120])
    ROWS.append(dict(d=d, tour=b[0]['short'], st=st, run=run, wk=wkg(d), other=other, onset=float(e['onset']), fire=float(e['fire']), s=s,
                     bs=busy[0] * 10 if busy else None, be=busy[-1] * 10 if busy else None, pk=int(I0 + np.argmax(s[I0:])) * 10, hasbusy=bool(busy)))
R = pd.DataFrame(ROWS); print('저녁', len(R), '투어', R.tour.nunique(), '혼잡 있던 저녁', int(R.hasbusy.sum()), file=sys.stderr)
def from_curve(c):
    b = [i for i in range(I0, 36) if c[i] >= THR]; return (b[0] * 10 if b else None, int(I0 + np.argmax(c[I0:])) * 10, b[-1] * 10 if b else None)
def med(T, k):
    v = T[k].dropna(); return float(np.median(v)) if len(v) else None
def models(T, q):
    """T: 학습 저녁(같은 투어 뺌), q: 맞힐 저녁(st, run, wk, other, fire). 반환: {모델: (혼잡 시작, 최대, 끝) 시작 뒤 분}"""
    out = {}; TB = T[T.hasbusy]
    out['M1 시작 기준 중앙값'] = (med(TB, 'bs'), med(T, 'pk'), med(TB, 'be'))
    if q['run'] == q['run']:
        r = q['run']; TT = TB[TB.run.notna()]; TP = T[T.run.notna()]
        out['M2 예정 종료 기준'] = (r + float(np.median(TT.bs - TT.run)), r + float(np.median(TP.pk - TP.run)), r + float(np.median(TT.be - TT.run)))
    near = T[(T.st - q['st']).abs() <= 60]; nb = near[near.hasbusy]
    if len(near) >= 5 and len(nb) >= 3: out['M3 시작 시각대(±1시간)'] = (med(nb, 'bs'), med(near, 'pk'), med(nb, 'be'))
    X = np.c_[T.st / 60, T.run.fillna(T.run.median()) / 30, T.wk * 1.0, np.minimum(T.other, 1) * 1.0]; x = np.array([q['st'] / 60, (q['run'] if q['run'] == q['run'] else T.run.median()) / 30, q['wk'], min(q['other'], 1)])
    dd = np.sqrt(((X - x) ** 2).sum(1)); idx = np.argsort(dd)[:12]; K = T.iloc[idx]; KB = K[K.hasbusy]
    out['M4 비슷한 공연 12개'] = (med(KB, 'bs') if len(KB) else None, med(K, 'pk'), med(KB, 'be') if len(KB) else None)
    out['M5 평균 곡선(시작 정렬)'] = from_curve(np.mean(np.vstack(T.s.values), axis=0))
    if q['run'] == q['run']:
        sh = []
        for _, t in T[T.run.notna()].iterrows():
            k = int(round((q['run'] - t.run) / 10)); c = np.roll(t.s, k)
            if k > 0: c[:k] = t.s[0]
            elif k < 0: c[k:] = t.s[-1]
            sh.append(c)
        out['M6 평균 곡선(종료 정렬)'] = from_curve(np.mean(np.vstack(sh), axis=0))
    base = [v for k, v in out.items()]
    ens = tuple(float(np.median([v[i] for v in base if v[i] is not None])) if any(v[i] is not None for v in base) else None for i in range(3))
    out['M7 앙상블(중앙값)'] = ens
    return out
def live_model(T, fire):
    """M8 실시간 감지 보정: 주차 감지(10분 6.5% 감소)가 울린 시각 + 2025 (최대 − 감지) 중앙값. 공연 중에는 못 내고 감지 뒤에 냄."""
    TB = T[T.hasbusy]
    return (fire + float(np.median(TB.bs - TB.fire)), fire + float(np.median(T.pk - T.fire)), fire + float(np.median(TB.be - TB.fire)))
# 검증: 같은 투어를 통째로 뺌
err = {};
for i, r in R.iterrows():
    T = R[R.tour != r.tour]; q = dict(st=r.st, run=r.run, wk=r.wk, other=r.other)
    M = models(T, q); M['M8 실시간 감지 보정(감지 뒤)'] = live_model(T, r.fire)
    for m, (bs, pk, be) in M.items():
        e = err.setdefault(m, dict(pk=[], bs=[], be=[], iou=[]))
        if pk is not None: e['pk'].append(abs(pk - r.pk))
        if r.hasbusy and bs is not None and be is not None:
            e['bs'].append(abs(bs - r.bs)); e['be'].append(abs(be - r.be))
            a0, a1, b0, b1 = bs, be + 10, r.bs, r.be + 10; inter = max(0, min(a1, b1) - max(a0, b0)); uni = max(a1, b1) - min(a0, b0); e['iou'].append(inter / uni if uni > 0 else 0)
res = {}
for m, e in err.items():
    f = lambda a: (round(float(np.median(a)), 0), round(float(np.mean(np.array(a) <= 20)) * 100, 0)) if a else (None, None)
    res[m] = dict(n_pk=len(e['pk']), pk_med_err=f(e['pk'])[0], pk_hit20=f(e['pk'])[1], n_busy=len(e['bs']), bs_med_err=f(e['bs'])[0], bs_hit20=f(e['bs'])[1], be_med_err=f(e['be'])[0], be_hit20=f(e['be'])[1], iou=round(float(np.mean(e['iou'])), 2) if e['iou'] else None)
# 오늘 밤 예측: 11/27 19:00 시작, 예정 130분, 평일(금), 올림픽홀 20:00 공연 있음
q = dict(st=19 * 60, run=130.0, wk=0, other=1); M = models(R, q)
clk = lambda m: None if m is None else f'{int((19*60+m)//60):02d}:{int((19*60+m)%60):02d}'
tonight = {k: dict(혼잡_시작=clk(v[0]), 최대=clk(v[1]), 혼잡_끝=clk(v[2])) for k, v in M.items()}
lv = dict(bs=float(np.median(R[R.hasbusy].bs - R[R.hasbusy].fire)), pk=float(np.median(R.pk - R.fire)), be=float(np.median(R[R.hasbusy].be - R[R.hasbusy].fire)))
json.dump(dict(backtest=res, tonight=tonight, live_rule_offsets_from_fire=lv, n_evenings=len(R), n_tours=int(R.tour.nunique()), n_busy=int(R.hasbusy.sum())), sys.stdout, ensure_ascii=False, indent=1)
