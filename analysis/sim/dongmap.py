"""2024 공원 인구 정답 만들기: 2025에 공원 값(poi127)과 동 11710566 값의 관계를 배워 2024 동 값을 공원 크기로 옮김.
방법 A: 공원 = 동 − 차이(날 종류×시각 중앙값). 방법 B: 공원 = a(날 종류×시각) + b·동. 2025 공연 날 15~24시에서 한 달씩 숨겨 확인."""
import json, pickle, os, numpy as np, pandas as pd
d = pd.read_csv('livingpop_songpa_2024_2025.csv', encoding='utf-8-sig', dtype={'dong': str, 'date': str, 'hour': str})
d = d[d.dong == '11710566']; d['ts'] = pd.to_datetime(d.date + d.hour, format='%Y%m%d%H'); dong = d.set_index('ts').total.sort_index()
p = pd.read_csv('checks/park_population_2025_hourly_poi127.csv', encoding='utf-8-sig'); p['ts'] = pd.to_datetime(p.ts); park = p.set_index('ts').park_pop
HOL = {r[:4] + '-' + r[4:6] + '-' + r[6:] for r in pd.read_csv('holidays.csv', dtype=str).iloc[:, 0]}
P = pickle.load(open(os.path.expanduser('~/past3.pkl'), 'rb')); SHOW = P['show']
show25 = {k for k, v in SHOW.items() if any('KSPO' in b['venue'] for b in v.get('big', []))}
def dt(ts):
    s = str(ts.date()); w = ts.weekday()
    return 'hol' if (w == 6 or s in HOL) else 'sat' if w == 5 else 'fri' if w == 4 else 'wk'
J = pd.DataFrame({'dong': dong, 'park': park}).dropna(); J['k'] = [dt(t) for t in J.index]; J['h'] = J.index.hour; J['m'] = J.index.month; J['day'] = J.index.strftime('%Y-%m-%d')
J['show'] = J.day.isin(show25)
res = {'A': [], 'B': []}
for m in range(1, 13):
    tr = J[(J.m != m)]; te = J[(J.m == m) & J.show & (J.h >= 15)]
    if not len(te): continue
    off = (tr[~tr.show].dong - tr[~tr.show].park).groupby([tr[~tr.show].k, tr[~tr.show].h]).median()
    pa = te.dong - off.reindex(pd.MultiIndex.from_arrays([te.k, te.h])).values
    res['A'] += list(np.abs(pa - te.park) / te.park)
    pb = []
    for (k, h), g in te.groupby(['k', 'h']):
        t = tr[(tr.k == k) & (tr.h == h)]; b, a = np.polyfit(t.dong, t.park, 1); pb += list(np.abs(a + b * g.dong - g.park) / g.park)
    res['B'] += pb
print({k: (round(float(np.mean(v)) * 100, 1), round(float(np.median(v)) * 100, 1), len(v)) for k, v in res.items()})
# 공연 날 저녁 증가분 비교(동 vs 공원): 18~21시 − 3~4시
e = J[J.show]; g = e.groupby('day')
inc = pd.DataFrame({'dong': g.apply(lambda x: x[x.h.between(19, 21)].dong.mean() - x[x.h.between(3, 4)].dong.mean()), 'park': g.apply(lambda x: x[x.h.between(19, 21)].park.mean() - x[x.h.between(3, 4)].park.mean())})
print('공연 저녁 증가분 동/공원 중앙값', round(float((inc.dong / inc.park).median()), 3), 'n', len(inc))
