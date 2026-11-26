"""퇴장 시뮬레이션 맞추기용 실측(2025, KSPO DOME 저녁 71개): 출차 5분 수, 늘어난 차, 티켓, 출차 시작.
출차 시작은 시뮬레이션과 같은 방법: 5분 출차 수의 10분 합이 가장 큰 칸에서 거꾸로 걸어가, 평소(처음 30분 중앙의 10분 합) + (최고 − 평소)의 30% 아래로 내려가기 직전 칸의 10분 앞.
사용: data 폴더에서 python3 ../analysis/egress_obs.py → checks/egress_obs.json"""
import json, pickle, os, numpy as np, pandas as pd
P = pickle.load(open(os.path.expanduser('~/past3.pkl'), 'rb')); SHOW = P['show']
E = json.load(open('checks/end_detect_2025.json')); EV = E['1~6월(정할 때 쓴 저녁)']['evenings'] + E['7·10·11월(채점)']['evenings']
df = pd.read_csv('inout_2025_full.csv', usecols=['entry_gate', 'entry_time', 'exit_time'], encoding='utf-8-sig'); df = df[~df.entry_gate.str.contains('CMB')]
df['x'] = pd.to_datetime(df.exit_time, errors='coerce'); df['e'] = pd.to_datetime(df.entry_time, errors='coerce')
K = pd.read_csv('../analysis/kopis_daily_2025.csv'); K = K[K.prfnmplc.str.contains('KSPO') & (K.prfdtcnt == 1)]
TK = {pd.Timestamp(str(a)).strftime('%Y-%m-%d'): b for a, b in zip(K['from'], K.totnmrs) if b > 0}
hm = lambda t: int(t[:2]) * 60 + int(t[3:])
def onset(ex5):  # ex5: 5분 출차 수(시작 60분 뒤부터)
    s = pd.Series(ex5); r = s + s.shift(1); ip = int(r.idxmax()); b10 = 2 * float(np.median(ex5[:6])); thr = b10 + 0.3 * (r[ip] - b10); i = ip
    while i - 1 >= 1 and r[i - 1] >= thr: i -= 1
    return i - 2  # 10분 앞
rows = []; curves = []
for ev in EV:
    d = ev['d']; s = SHOW[d]['big'][0]; st = pd.Timestamp(d) + pd.Timedelta(minutes=hm(s['t']))
    w = df[(df.x >= st + pd.Timedelta(minutes=60)) & (df.x < st + pd.Timedelta(hours=7))]
    b = ((w.x - st).dt.total_seconds() // 300).astype(int) - 12
    ex5 = b.value_counts().reindex(range(0, 72), fill_value=0).values
    on = onset(ex5)
    base = ex5[max(0, on - 6):on].mean() if on > 0 else ex5[:3].mean()
    post = np.clip(ex5[on:on + 24] - base, 0, None)
    if len(post) < 24 or post.sum() <= 0: continue
    cum = np.cumsum(post) / post.sum()
    occ_on = int(((df.e <= st + pd.Timedelta(minutes=60 + 5 * on)) & ((df.x > st + pd.Timedelta(minutes=60 + 5 * on)) | df.x.isna())).sum())
    rows.append(dict(d=d, start=s['t'], onset_after_start=60 + 5 * on, base5=base, excess=float(post.sum()), peak5=int(ex5[on:on + 24].max()), tickets=TK.get(d), occ_on=occ_on))
    curves.append(cum)
R = pd.DataFrame(rows); C = np.array(curves)
R['cars_per_1000'] = 1000 * R.excess / R.tickets
out = dict(n=len(R), cum_median=np.median(C, axis=0).round(4).tolist(), cum_p25=np.percentile(C, 25, axis=0).round(4).tolist(), cum_p75=np.percentile(C, 75, axis=0).round(4).tolist(),
           excess_med=float(R.excess.median()), tickets_med=float(R.tickets.median()), cars_per_1000_med=float(R.cars_per_1000.median()), cars_per_1000_q=[float(R.cars_per_1000.quantile(.1)), float(R.cars_per_1000.quantile(.9))],
           peak5_med=float(R.peak5.median()), base5_med=float(R.base5.median()), occ_on_med=float(R.occ_on.median()))
print(json.dumps({k: v for k, v in out.items() if not k.startswith('cum')}, ensure_ascii=False))
print('누적 %(5분마다, 출차 시작 뒤):', [round(100 * v) for v in out['cum_median']])
R.to_csv('checks/egress_obs_evenings.csv', index=False); json.dump(out, open('checks/egress_obs.json', 'w'), ensure_ascii=False, indent=1)
# --- 같은 감지 규칙(10분 전보다 6.5% 이상 감소, 시작 60분 뒤부터)을 실측 주차 점유에 적용해 '감지 − 출차 시작'을 같은 정의로 잼
ES, XS = np.sort(df.e.dropna().values), np.sort(df.x.dropna().values)
occ = lambda ts: int(np.searchsorted(ES, np.datetime64(ts)) - np.searchsorted(XS, np.datetime64(ts)))
fm = []
for _, r in R.iterrows():
    s = SHOW[r.d]['big'][0]; st = pd.Timestamp(r.d) + pd.Timedelta(minutes=hm(s['t'])); fire = None
    for k in range(13, 84):
        t = st + pd.Timedelta(minutes=5 * k); a, b = occ(t - pd.Timedelta(minutes=10)), occ(t)
        if a - b >= 0.065 * max(a, 1): fire = 5 * k; break
    fm.append(np.nan if fire is None else fire - r.onset_after_start)
R['fire_minus_onset'] = fm
print('실측 감지 − 출차 시작(같은 정의): 중앙 %.0f분, 10~90%% %.0f ~ %.0f분, %d저녁' % (R.fire_minus_onset.median(), R.fire_minus_onset.quantile(.1), R.fire_minus_onset.quantile(.9), R.fire_minus_onset.notna().sum()))
out['fire_minus_onset_med'] = float(R.fire_minus_onset.median()); out['fire_minus_onset_q'] = [float(R.fire_minus_onset.quantile(.1)), float(R.fire_minus_onset.quantile(.9))]
R.to_csv('checks/egress_obs_evenings.csv', index=False); json.dump(out, open('checks/egress_obs.json', 'w'), ensure_ascii=False, indent=1)
