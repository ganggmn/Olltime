"""지난 공연 저녁 199개(sim.mjs와 같은 재현)에서 사람 수 2시간 앞 예상을 '현재값 유지'와 견줌(2026-11-28).
현재값 유지: 2시간 전에 손에 있던 마지막 서울시식 범위의 가운데(정답 시간값 → 1만 미만 500명·이상 2,000명 칸, 30분 늦게 들어옴).
채점은 sim.mjs와 같음: 15:00~23:40, 20분 칸 27개, 정답 = 측정 시각(30분 앞) 시간값 보간. 지금 사이트(main)·새 방식(new) 오차는 sim_out.json 그대로.
공연 단위 신뢰구간: 같은 공연(이름) 묶음을 통째로 다시 뽑는 재표집 4,000번.
사용: 맥 bt 폴더(sim_in.json, sim_out.json 있는 곳)에서 python3 <이 파일>"""
import json, os, numpy as np
IN = json.load(open(os.path.expanduser('~/bt/sim_in.json'))); OUT = json.load(open(os.path.expanduser('~/bt/sim_out.json')))['per']
def tAt(tr, t):
    x = t / 60 - 0.5
    if x <= 0: return tr[0]
    if x >= 23: return tr[23]
    i = int(np.floor(x)); return tr[i] + (tr[i + 1] - tr[i]) * (x - i)
def mid(v): w = 500 if v < 10000 else 2000; lo = np.floor(v / w) * w; return lo + w / 2
per = {(p['yr'], p['d']): p for p in OUT}
rows = []
for yr in ('2025', '2024'):
    for e in IN[yr]:
        p = per[(yr, e['d'])]; S = [m for m in range(0, 1441, 20) if 900 <= m <= 1435]
        ae = [abs(mid(tAt(e['truth'], m - 150)) - tAt(e['truth'], m - 30)) for m in S]; tv = [tAt(e['truth'], m - 30) for m in S]
        rows.append(dict(yr=yr, d=e['d'], name=e['name'], n=p['main']['n'], main=p['main']['mae'], new=p['new']['mae'], pers=float(np.mean(ae)), tmean=float(np.mean(tv)), pn=len(S)))
rng = np.random.default_rng(20261128); res = {}
for yr in ('2025', '2024'):
    R = [r for r in rows if r['yr'] == yr]; G = {}
    for r in R: G.setdefault(r['name'], []).append(r)
    names = list(G)
    def agg(rs, k): return sum(r[k] * r['n'] for r in rs) / sum(r['n'] for r in rs)
    B = []
    for _ in range(4000):
        rs = [r for i in rng.integers(0, len(names), len(names)) for r in G[names[i]]]
        B.append([agg(rs, 'main'), agg(rs, 'new'), agg(rs, 'pers'), agg(rs, 'main') - agg(rs, 'pers'), agg(rs, 'new') - agg(rs, 'pers')])
    B = np.array(B); q = lambda c, a, b: [float(np.percentile(B[:, c], a)), float(np.percentile(B[:, c], b))]
    r = dict(evenings=len(R), shows=len(names), main=agg(R, 'main'), new=agg(R, 'new'), pers=agg(R, 'pers'), mean_truth=agg(R, 'tmean'),
             main_ci95=q(0, 2.5, 97.5), new_ci95=q(1, 2.5, 97.5), pers_ci95=q(2, 2.5, 97.5),
             main_minus_pers_ci95=q(3, 2.5, 97.5), main_minus_pers_ci99=q(3, .5, 99.5), new_minus_pers_ci95=q(4, 2.5, 97.5), new_minus_pers_ci99=q(4, .5, 99.5),
             main_win=sum(x['main'] < x['pers'] for x in R), new_win=sum(x['new'] < x['pers'] for x in R))
    res[yr] = r
    print('%s 공연 저녁 %d개(공연 %d개) | MAE 지금 사이트 %.0f명(95%% %.0f~%.0f) · 새 방식 %.0f명(%.0f~%.0f) · 현재값 유지 %.0f명(%.0f~%.0f) | 사이트−유지 %+.0f(95%% %+.0f~%+.0f, 99%% %+.0f~%+.0f) · 새−유지 %+.0f(95%% %+.0f~%+.0f, 99%% %+.0f~%+.0f) | 유지보다 나은 저녁 사이트 %d · 새 %d / %d | 평균 정답 %.0f명' % (
        yr, r['evenings'], r['shows'], r['main'], *r['main_ci95'], r['new'], *r['new_ci95'], r['pers'], *r['pers_ci95'], r['main'] - r['pers'], *r['main_minus_pers_ci95'], *r['main_minus_pers_ci99'],
        r['new'] - r['pers'], *r['new_minus_pers_ci95'], *r['new_minus_pers_ci99'], r['main_win'], r['new_win'], r['evenings'], r['mean_truth']))
json.dump(res, open(os.path.expanduser('~/bt/sim_pers.json'), 'w'), ensure_ascii=False, indent=1)
