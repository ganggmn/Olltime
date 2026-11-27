"""큰 공연 날 2시간 앞 주차 예측 MAE를 사이트 방식 그대로 2025년 지난 기록으로 시험(2026-11-28).
사이트 방식(model.js ③): 2025 같은 종류 날의 20분 칸 중앙값 모양 + (2시간 전 실제 − 그때 모양) × 0.85(BETA.show 2시간).
  - 날 종류는 gatep.py와 같음(일·공휴일 hol, 토 sat, 금 fri, 월~목 wk, 관객 9,000명 이상이면 _show). 사이트의 clsOf처럼 월~목 공연 날은 wk 모양을 씀.
  - 그날은 모양에서 빼고(하루 빼기) 맞힘. 단위는 2025 입출차(북2·동2·남2문, 머문 시간 10분~3일)로 센 주차장 안 차량 수.
  - 현재값 유지: 2시간 전 실제 값을 그대로.
  - 공연 단위 신뢰구간: 같은 공연(이름이 같은 날 묶음)을 통째로 다시 뽑는 재표집 4,000번.
사용: data 폴더에서 python3 ../analysis/park_show_2h.py"""
import json, os, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
df = pd.read_csv('inout_2025_full.csv', usecols=['entry_gate', 'entry_time', 'exit_time'], encoding='utf-8-sig')
e = pd.to_datetime(df.entry_time); x = pd.to_datetime(df.exit_time); st = (x - e).dt.total_seconds() / 60
g = df.entry_gate.astype(str).str.split('입구').str[0]; ok = (st >= 10) & (st < 4320) & g.isin(['북2문', '동2문', '남2문'])
es = np.sort(e[ok].values); xs = np.sort(x[ok].values)
L = pd.read_csv('linked_2025.csv', encoding='utf-8-sig', usecols=['datetime', 'perf_name', 'perf_audience']); L = L[L.perf_name.notna() & (L.perf_name != '')]
aud = L.groupby(L.datetime.str[:10]).perf_audience.max(); nm = L.sort_values('perf_audience').groupby(L.datetime.str[:10]).perf_name.last()
hol = {r[:4] + '-' + r[4:6] + '-' + r[6:] for r in pd.read_csv('holidays.csv', dtype=str).iloc[:, 0]}
days = [d.strftime('%Y-%m-%d') for d in pd.date_range('2025-01-02', '2025-10-30')]; days = [d for d in days if d[5:7] not in ('08', '09') and d[8:] not in ('28', '29', '30', '31')]
def base(d): wd = pd.Timestamp(d).weekday(); return 'hol' if (d in hol or wd == 6) else 'sat' if wd == 5 else 'fri' if wd == 4 else 'wk'
show = {d: aud.get(d, 0) >= 9000 for d in days}
cls = {d: base(d) + ('_show' if show[d] and base(d) != 'wk' else '') for d in days}
SL = np.arange(0, 1440, 20)
def occ(d):
    t = (np.datetime64(d + 'T00:00') + SL.astype('timedelta64[m]'))
    return (np.searchsorted(es, t, 'right') - np.searchsorted(xs, t, 'right')).astype(float)
OC = {d: occ(d) for d in days}
print('날 종류별 날수', pd.Series(cls).value_counts().to_dict())
B2 = 0.85; LAG = 6  # 2시간 = 20분 칸 6개
rows = []
for d in days:
    if not show[d]: continue
    pool = [k for k in days if k != d and cls[k] == cls[d]]
    prof = np.median([OC[k] for k in pool], axis=0); y = OC[d]
    for i in range(LAG, len(SL)):
        m = SL[i]
        if m < 420 or m > 1380: continue
        f = max(0.0, prof[i] + B2 * (y[i - LAG] - prof[i - LAG]))
        rows.append(dict(d=d, name=nm.get(d, ''), m=int(m), truth=y[i], main=f, pers=y[i - LAG], prof=prof[i], cls=cls[d], aud=float(aud.get(d, 0))))
R = pd.DataFrame(rows); R['eve'] = R.m >= 900
R.to_csv(os.path.expanduser('~/bt/park_show_2h_rows.csv'), index=False)
rng = np.random.default_rng(20261128)
def boot(Rs, key=('main', 'pers'), n=4000):
    G = {k: v for k, v in Rs.groupby('name')}; names = list(G); out = []
    for _ in range(n):
        S = pd.concat([G[names[i]] for i in rng.integers(0, len(names), len(names))])
        a, b = np.abs(S[key[0]] - S.truth).mean(), np.abs(S[key[1]] - S.truth).mean(); out.append((a, b, a - b))
    return np.array(out)
res = {}
for lab, Rs in (('하루(07~23시)', R), ('공연 저녁(15~23시)', R[R.eve])):
    a, b = np.abs(Rs.main - Rs.truth), np.abs(Rs.pers - Rs.truth); bt = boot(Rs)
    q = lambda c, p: np.percentile(bt[:, c], p)
    res[lab] = dict(days=int(Rs.d.nunique()), shows=int(Rs.name.nunique()), n=int(len(Rs)), mae=a.mean(), mae_ci95=[q(0, 2.5), q(0, 97.5)], mape=100 * (a / Rs.truth.clip(lower=1)).mean(), mdae=float(a.median()),
                    pers_mae=b.mean(), pers_ci95=[q(1, 2.5), q(1, 97.5)], diff=a.mean() - b.mean(), diff_ci95=[q(2, 2.5), q(2, 97.5)], diff_ci99=[q(2, 0.5), q(2, 99.5)],
                    win_days=int(Rs.assign(a=a, b=b).groupby('d').apply(lambda z: z.a.mean() < z.b.mean()).sum()),
                    mean_truth=float(Rs.truth.mean()))
    r = res[lab]
    print('%s: 공연 날 %d일·공연 %d개·%d칸 | 사이트 MAE %.0f대(95%% %.0f~%.0f), MAPE %.1f%%, 중앙 절대 오차 %.0f대 | 현재값 유지 MAE %.0f대(95%% %.0f~%.0f) | 차이 %+.0f대(95%% %+.0f~%+.0f, 99%% %+.0f~%+.0f) | 사이트가 나은 날 %d/%d | 평균 정답 %.0f대' % (
        lab, r['days'], r['shows'], r['n'], r['mae'], *r['mae_ci95'], r['mape'], r['mdae'], r['pers_mae'], *r['pers_ci95'], r['diff'], *r['diff_ci95'], *r['diff_ci99'], r['win_days'], r['days'], r['mean_truth']))
json.dump(res, open(os.path.expanduser('~/bt/park_show_2h.json'), 'w'), ensure_ascii=False, indent=1, default=float)
