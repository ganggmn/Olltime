"""가설: '첫날은 언제 갈지 몰라 도착이 퍼지고, 같은 공연 다음 날부터는 사람들이 배워서 도착이 더 모인다(세련된 모양)'를 검증(탐색, 결과 보기 전 기준을 아래에 적음).
자료: 서울 체류인구(250m, KT) 2025 1년치, KSPO DOME 칸에 3시간 넘게 머문 사람의 시각별 도착(같은 달 공연 없는 날 중앙값을 뺌), 시작 6시간 전~시작 시각대. 출처: 서울특별시·KT, 서울시 통신데이터.
날마다 재는 것(시작 기준 시각 r = −6…0, 몫 p_r):
  중심 = Σ r·p_r(시간, 음수일수록 일찍), 퍼짐 = 표준편차(시간), 최고 몫 = max p_r, 엔트로피 = −Σ p log p(작을수록 모임)
가설이 맞다면: 둘째 날 이후 퍼짐·엔트로피 ↓, 최고 몫 ↑. (중심은 방향을 미리 정하지 않음)
비교(투어 = 같은 공연 묶음):
  ① 바로 다음 날 − 앞날, 둘 다 주말·공휴일이고 시작 시각 차이 1시간 이하인 쌍만(요일·시각 영향 줄임)
  ② 투어마다 평균을 빼고(투어 고정 효과) '둘째 날 이후' 계수를 봄, 주말 여부·시작 시각을 함께 넣음
  구간: 투어 묶음 재표집 10,000번(seed 0), 95%·99%. 네 지표 p는 홀름 보정.
사용: data 폴더에서 python3 ../analysis/stay_learning.py → checks/stay_learning.json"""
import os, io, sys, json, runpy, contextlib, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from sigtest import holm
with contextlib.redirect_stdout(io.StringIO()): g = runpy.run_path(os.path.join(HERE, 'stay_year.py'), run_name='x')
L, S, SHOW = g['L'], g['S'].copy(), g['SHOW']
dome = g['dome']; months = sorted({d[:7] for d in L.index})
BASE = {m: L.loc[[d for d in L.index if d[:7] == m and not dome(d)]].median() for m in months}
R = np.arange(-6, 1); rows = []
for _, r in S.iterrows():
    sh = int(r.start[:2]); A = (L.loc[r.d] - BASE[r.d[:7]]).clip(lower=0).loc[sh - 6:sh].values; p = A / A.sum()
    c = float((R * p).sum()); sd = float(np.sqrt(((R - c) ** 2 * p).sum())); ent = float(-(p[p > 0] * np.log(p[p > 0])).sum())
    rows.append(dict(d=r.d, name=r['name'], seq=int(r.seq), wkend=bool(r.wkend), start=sh + int(r.start[3:5]) / 60, centroid=c, spread=sd, peak=float(p.max()), entropy=ent))
D = pd.DataFrame(rows); MET = ['spread', 'entropy', 'peak', 'centroid']
multi = D.groupby('name').name.transform('size') >= 2; D = D[multi]
print('투어 %d개, 날 %d일(첫날 %d, 둘째 날 이후 %d)' % (D.name.nunique(), len(D), (D.seq == 1).sum(), (D.seq >= 2).sum()))
print('평균: ' + ' | '.join('%s 첫날 %.3f / 이후 %.3f' % (m, D[D.seq == 1][m].mean(), D[D.seq >= 2][m].mean()) for m in MET))
rng = np.random.default_rng(0); B = 10000
def boot_mean(df, col, key='name'):
    keys = df[key].unique(); grp = {k: df[df[key] == k][col].values for k in keys}; v = np.empty(B)
    for b in range(B):
        pick = rng.choice(keys, len(keys)); x = np.concatenate([grp[k] for k in pick]); v[b] = x.mean()
    est = df[col].mean(); p = min(1.0, 2 * min((v <= 0).mean(), (v >= 0).mean())); p = max(p, 1 / B)
    return est, np.percentile(v, [2.5, 97.5]), np.percentile(v, [0.5, 99.5]), p
out = {}
# ① 다음 날 − 앞날, 둘 다 주말·공휴일, 시작 차이 ≤ 1시간
P = []
for n, gd in D.sort_values('d').groupby('name'):
    gd = gd.reset_index(drop=True)
    for i in range(1, len(gd)):
        a, b = gd.loc[i - 1], gd.loc[i]
        if (pd.Timestamp(b.d) - pd.Timestamp(a.d)).days == 1 and a.wkend and b.wkend and abs(a.start - b.start) <= 1:
            P.append(dict(name=n, d0=a.d, d1=b.d, firstpair=a.seq == 1, **{m: b[m] - a[m] for m in MET}))
P = pd.DataFrame(P); print('\n== ① 바로 다음 날 − 앞날(둘 다 주말·공휴일, 시작 차이 1시간 이하): 쌍 %d개, 투어 %d개 (그중 첫날→둘째 날 %d쌍)' % (len(P), P.name.nunique(), P.firstpair.sum()))
ps = []; res1 = {}
for m in MET:
    est, ci95, ci99, p = boot_mean(P, m); ps.append(p); res1[m] = dict(diff=est, ci95=ci95.tolist(), ci99=ci99.tolist(), p=p)
for m, pa in zip(MET, holm(ps)):
    r = res1[m]; r['p_holm'] = pa
    print('  %-8s 차이 %+.3f | 95%% %+.3f ~ %+.3f | 99%% %+.3f ~ %+.3f | p=%.3f, 홀름 %.3f' % (m, r['diff'], *r['ci95'], *r['ci99'], r['p'], pa))
out['pairs_weekend'] = res1
# ①' 첫날→둘째 날 쌍만
Q = P[P.firstpair]
if len(Q) >= 5:
    print('  (첫날→둘째 날 쌍만 %d개) ' % len(Q) + ' | '.join('%s %+.3f' % (m, Q[m].mean()) for m in MET))
# ② 투어 고정 효과: 투어 안에서 평균을 빼고 later·주말·시작 시각으로 회귀, 투어 묶음 재표집
D['later'] = (D.seq >= 2).astype(float); D['wk'] = D.wkend.astype(float)
def coef(df, m):
    X = df[['later', 'wk', 'start']].astype(float); y = df[m]
    Xc = X - X.groupby(df.name).transform('mean'); yc = y - y.groupby(df.name).transform('mean')
    bta, *_ = np.linalg.lstsq(Xc.values, yc.values, rcond=None); return bta[0]
print('\n== ② 투어 안에서 비교(주말·시작 시각 함께 뺌): 둘째 날 이후 − 첫날')
ps = []; res2 = {}; keys = D.name.unique(); grp = {k: D[D.name == k] for k in keys}
for m in MET:
    est = coef(D, m); v = np.empty(2000)
    for b in range(2000):
        pick = rng.choice(keys, len(keys)); x = pd.concat([grp[k].assign(name='%s#%d' % (k, j)) for j, k in enumerate(pick)]); v[b] = coef(x, m)
    p = max(min(1.0, 2 * min((v <= 0).mean(), (v >= 0).mean())), 1 / 2000); ps.append(p)
    res2[m] = dict(coef=float(est), ci95=np.percentile(v, [2.5, 97.5]).tolist(), ci99=np.percentile(v, [0.5, 99.5]).tolist(), p=p)
for m, pa in zip(MET, holm(ps)):
    r = res2[m]; r['p_holm'] = pa
    print('  %-8s %+.3f | 95%% %+.3f ~ %+.3f | 99%% %+.3f ~ %+.3f | p=%.3f, 홀름 %.3f' % (m, r['coef'], *r['ci95'], *r['ci99'], r['p'], pa))
out['fixed_effects'] = res2
D.round(4).to_csv('checks/stay_learning_days.csv', index=False); json.dump(out, open('checks/stay_learning.json', 'w'), ensure_ascii=False, indent=1, default=float)
