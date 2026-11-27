import json, os, numpy as np
o = json.load(open(os.path.expanduser('~/bt/sim_out.json'))); I = json.load(open(os.path.expanduser('~/bt/sim_in.json')))
TR = {e['d']: e for y in I for e in I[y]}
def tAt(tr, t):
    x = t / 60 - 0.5
    if x <= 0: return tr[0]
    if x >= 23: return tr[23]
    i = int(np.floor(x)); return tr[i] + (tr[i + 1] - tr[i]) * (x - i)
rng = np.random.default_rng(7); res = {}
for yr in ('2025', '2024'):
    P = [p for p in o['per'] if p['yr'] == yr]; rows = []
    for p in P:
        c = o['charts'][p['d']]; mm = dict(map(tuple, c['main'])); nn = dict(map(tuple, c['new'])); tr = TR[p['d']]['truth']
        st = p['st']; end = st + (p['run'] or 150)
        ph = {'공연 전(15시~시작)': lambda m: 900 <= m - 30 < st, '공연 중': lambda m: st <= m - 30 < end, '끝난 뒤(~24시)': lambda m: end <= m - 30 and m <= 1435}
        r = {'d': p['d'], 'name': p['name']}
        for k, f in ph.items():
            ms = [m for m in mm if m in nn and f(m)]
            a = np.array([tAt(tr, m - 30) for m in ms]); e0 = np.abs(np.array([mm[m] for m in ms]) - a); e1 = np.abs(np.array([nn[m] for m in ms]) - a)
            r[k] = (e0.sum(), e1.sum(), a.sum(), len(ms))
        r['all'] = tuple(np.sum([r[k][i] for k in ph], axis=0) for i in range(4)); rows.append(r)
    names = sorted({r['name'] for r in rows}); byn = {n: [i for i, r in enumerate(rows) if r['name'] == n] for n in names}
    out = {}
    for k in ['all', '공연 전(15시~시작)', '공연 중', '끝난 뒤(~24시)']:
        E0 = np.array([r[k][0] for r in rows]); E1 = np.array([r[k][1] for r in rows]); A = np.array([r[k][2] for r in rows]); N = np.array([r[k][3] for r in rows])
        acc = lambda e, i: 100 * (1 - e[i].sum() / A[i].sum())
        idx = np.arange(len(rows)); obs = acc(E1, idx) - acc(E0, idx); bs = []
        for _ in range(4000):
            ii = np.concatenate([byn[n] for n in rng.choice(names, len(names))]); bs.append(acc(E1, ii) - acc(E0, ii))
        out[k] = dict(acc_main=round(acc(E0, idx), 1), acc_new=round(acc(E1, idx), 1), mae_main=round(E0.sum() / N.sum()), mae_new=round(E1.sum() / N.sum()),
                      diff=round(obs, 1), ci95=[round(np.percentile(bs, 2.5), 1), round(np.percentile(bs, 97.5), 1)], ci99=[round(np.percentile(bs, 0.5), 1), round(np.percentile(bs, 99.5), 1)],
                      better=int((E1 < E0).sum()), n=len(rows))
    res[yr] = dict(evenings=len(rows), shows=len(names), phases=out)
json.dump(res, open(os.path.expanduser('~/bt/sim_stat.json'), 'w'), ensure_ascii=False, indent=1)
for yr in res:
    print(yr, res[yr]['evenings'], '저녁', res[yr]['shows'], '공연')
    for k, v in res[yr]['phases'].items(): print('  %-14s 정확도 지금 %.1f → 새 %.1f (차 %+.1f%%p, 95%% %+.1f~%+.1f, 99%% %+.1f~%+.1f) 오차 %d→%d명, 새가 나은 저녁 %d/%d' % (k, v['acc_main'], v['acc_new'], v['diff'], *v['ci95'], *v['ci99'], v['mae_main'], v['mae_new'], v['better'], v['n']))
