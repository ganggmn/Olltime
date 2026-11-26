"""시간대마다 '지금 차이가 2시간 뒤에 얼마나 남는지'(β)를 2025년 생활인구로 재고 95% 신뢰구간을 붙여요.
사용: data 폴더에서 python3 ../analysis/beta_hour.py  → checks/beta_hour_2025.json
차이 = 그날 새벽 대비 증가 − 같은 날 종류의 시간별 중앙값(다른 날들로만 구함, 그날은 뺌).
β(h) = 시각 h의 차이로 h+2의 차이를 설명하는 기울기(원점을 지나는 직선). 날짜를 다시 뽑아 2,000번 → 95% 구간.
구간이 0을 끼면 '그 시각의 차이는 2시간 뒤에 남는다고 말할 수 없음' → 보정하지 않음(β=0)."""
import os, json, pickle, numpy as np, pandas as pd
P = pickle.load(open(os.path.expanduser('~/past3.pkl'), 'rb')); G = P['G']
PO = pd.read_csv('checks/park_population_2025_hourly_poi127_full.csv'); PO['ts'] = pd.to_datetime(PO.ts); PO['d'] = PO.ts.dt.strftime('%Y-%m-%d'); PO['h'] = PO.ts.dt.hour
Y = PO.pivot_table(index='d', columns='h', values='park_pop').dropna(); INC = Y.sub(Y[[2, 3, 4]].median(axis=1), axis=0)
out = {}
rng = np.random.default_rng(0)
for k, g in (('wk', ['월~목·없음']), ('noshow_we', ['토·없음', '일·없음', '금·없음']), ('show', ['금·큰 공연', '토·큰 공연', '일·큰 공연', '월~목·큰 공연'])):
    ds = [d for d in INC.index if G.get(d, '') in g]
    if len(ds) < 8: continue
    A = INC.loc[ds].values
    # 그날을 뺀 중앙값(남의 날들로 만든 모양)
    R = np.vstack([A[i] - np.median(np.delete(A, i, axis=0), axis=0) for i in range(len(ds))])
    res = []
    for h in range(5, 22):
        x, y = R[:, h], R[:, h + 2]
        b = float(np.sum(x * y) / np.sum(x * x))
        bs = []
        for _ in range(2000):
            idx = rng.integers(0, len(ds), len(ds)); xx, yy = x[idx], y[idx]; bs.append(np.sum(xx * yy) / np.sum(xx * xx))
        lo, hi = np.percentile(bs, [2.5, 97.5])
        res.append(dict(h=h, beta=round(b, 2), ci95=[round(float(lo), 2), round(float(hi), 2)], use=round(b, 2) if lo > 0 else 0.0, sd_resid=round(float(np.std(x)))))
    out[k] = dict(days=len(ds), hours=res)
    print('\n[%s] %d일. 시각 h의 차이가 h+2시에 남는 비율 β (95%% 구간) → 쓸 값' % (k, len(ds)))
    print('  ' + ' | '.join('%d→%d시 %.2f(%.2f~%.2f)→%.2f' % (r['h'], r['h'] + 2, r['beta'], r['ci95'][0], r['ci95'][1], r['use']) for r in res))
json.dump(out, open('checks/beta_hour_2025.json', 'w'), ensure_ascii=False, indent=1)
