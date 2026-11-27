"""우리 2시간 앞 사람 수 예상(새 방식)에 80% 예측 구간을 붙이면: 2025(모양 만든 해) 잔차로 구간을 정하고 2024(처음 보는 해)에서 담는 비율 확인.
잔차 = 실제 ÷ 예상 − 1, 구간 = 예상 × (1 + 10% 분위, 1 + 90% 분위). 구간(공연 전/중/끝난 뒤)별로 따로. 담는 비율의 95% 범위는 같은 공연 묶음 재표집 4,000번."""
import json, os, numpy as np
o = json.load(open(os.path.expanduser('~/bt/sim_out.json'))); I = json.load(open(os.path.expanduser('~/bt/sim_in.json')))
TR = {e['d']: e for y in I for e in I[y]}
def tAt(tr, t):
    x = t / 60 - 0.5
    if x <= 0: return tr[0]
    if x >= 23: return tr[23]
    i = int(np.floor(x)); return tr[i] + (tr[i + 1] - tr[i]) * (x - i)
def rows(yr, key):
    R = []
    for p in o['per']:
        if p['yr'] != yr: continue
        tr = TR[p['d']]['truth']; st = p['st']; en = st + (p['run'] or 150)
        for m, v in o['charts'][p['d']][key]:
            t = m - 30
            if t < 900 or m > 1435: continue
            ph = 'pre' if t < st else 'in' if t < en else 'post'
            if v > 0: R.append((p['name'], ph, v, tAt(tr, t)))
    return R
out = {}
for key in ('new', 'main'):
    A = rows('2025', key); B = rows('2024', key); res = {}
    for ph in ('pre', 'in', 'post', 'all'):
        a = [r for r in A if ph == 'all' or r[1] == ph]; b = [r for r in B if ph == 'all' or r[1] == ph]
        rel = np.array([t / v - 1 for _, _, v, t in a]); lo, hi = np.percentile(rel, [10, 90])
        cov = np.array([v * (1 + lo) <= t <= v * (1 + hi) for _, _, v, t in b]); wid = np.array([v * (hi - lo) for _, _, v, t in b])
        names = sorted({r[0] for r in b}); idx = {n: [i for i, r in enumerate(b) if r[0] == n] for n in names}; rng = np.random.default_rng(7); bs = []
        for _ in range(4000):
            ii = np.concatenate([idx[n] for n in rng.choice(names, len(names))]); bs.append(cov[ii].mean())
        res[ph] = dict(q10=round(lo * 100, 1), q90=round(hi * 100, 1), cover_2024=round(cov.mean() * 100, 1), ci95=[round(np.percentile(bs, 2.5) * 100, 1), round(np.percentile(bs, 97.5) * 100, 1)], width_med=int(np.median(wid)), n=len(b))
    out[key] = res
E = json.load(open(os.path.expanduser('~/mnt/(주)한국체육산업개발 공모전/data/checks/end_detect_2025.json')))
ev = E['1~6월(정할 때 쓴 저녁)']['evenings'] + E['7·10·11월(채점)']['evenings']
se = np.array([z['sched_err'] for z in ev]); out['sched_minus_onset'] = dict(sd=round(float(np.std(se, ddof=1)), 1), mad_med=float(np.median(np.abs(se - np.median(se)))), med=float(np.median(se)), p10=float(np.percentile(se, 10)), p90=float(np.percentile(se, 90)), n=len(se))
json.dump(out, open(os.path.expanduser('~/bt/pi80.json'), 'w'), ensure_ascii=False, indent=1)
for k in ('new', 'main'):
    print(k); [print('  ', ph, v) for ph, v in out[k].items()]
print('예정 종료 − 실제 출차 몰림 시작', out['sched_minus_onset'])
