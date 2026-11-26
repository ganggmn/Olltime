"""지금 기준 재검증 + 유의수준 0.01(2026-11-27). 공연 없는 월~목.
주차: 2025 입출차(북2·동2·남2문, bt_schedule.py와 같은 정리)로 30분마다 주차장 안 차량 수. 예상 = 같은 요일 공연 없는 다른 날들의 (그날 − 새벽 4시) 중앙값 + 그날 새벽 4시 값.
  2시간 앞 = 예상 + (2시간 전 실제 − 2시간 전 예상). 2025는 하루씩 빼고 맞힘(그날 빼고 같은 요일로 모양). 2026은 실시간 parking_sum(11/23~26).
인구: 2025는 ahead_2025.py(KT 생활인구, 앞선 달로만, 월~목), 2026은 live_recheck_pop.mjs 결과(서울시 실시간 → 올타임 추정, 사이트 방식).
유의수준 0.01: 2025 평균의 99% 구간(날 묶음 재표집), 하루 정확도 1% 지점(이보다 낮으면 '평소와 다르다'고 0.01로 말할 수 있는 선), 2026 네 날의 99% 구간(t, 자유도 3).
사용: data 폴더에서 python3 ../analysis/live_recheck.py"""
import io, contextlib, os, sys, json, datetime as dt, numpy as np, pandas as pd
from scipy import stats
with contextlib.redirect_stdout(io.StringIO()): exec(open('../analysis/bt_schedule.py', encoding='utf-8').read().split("T={'2026-11-13'")[0])
H = [i for i, t in enumerate(slots) if dt.time(7, 0) <= t <= dt.time(23, 0)]
big = set(S.index[S.aud >= 3500]); wkd = [d for d in alld if pd.Timestamp(d).weekday() < 4 and d not in big and d[5:7] != '01']  # 1월 뺌: 기록이 1/1부터라 그 전에 세운 차가 빠져 새벽 수준이 낮게 잡힘(가장 안 맞은 10일이 모두 1월, 새벽 60~164대)
OCC = {d: occ(d).astype(float) for d in wkd}; NT = {d: float(nt(d)) for d in wkd}
def acc(p, y): return 100 * (1 - np.abs(p - y).sum() / y.sum())
def two_h(p, y): q = p.copy(); q[4:] = p[4:] + (y[:-4] - p[:-4]); return q  # 30분 칸 4개 = 2시간
rows = []
for d in wkd:
    oth = [k for k in wkd if k != d and pd.Timestamp(k).weekday() == pd.Timestamp(d).weekday()]
    p = np.median([OCC[k] - NT[k] for k in oth], axis=0) + NT[d]; y = OCC[d]; q = two_h(p, y)
    rows.append(dict(d=d, dawn=acc(p[H], y[H]), h2=acc(q[H], y[H])))
P25 = pd.DataFrame(rows)
pk = pd.read_csv('parking/parking.csv'); pk['t'] = pd.to_datetime(pk.collected_at); pk = pk.dropna(subset=['parking_sum']).set_index('t').parking_sum.astype(float).sort_index()
live = []
for d in ['2026-11-23', '2026-11-24', '2026-11-25', '2026-11-26']:
    ts = pd.to_datetime([f'{d} {t}' for t in slots]); y = pk.reindex(pk.index.union(ts)).interpolate(limit=2).reindex(ts).values
    night = float(pk.reindex(pk.index.union([pd.Timestamp(f'{d} 04:00')])).interpolate().loc[f'{d} 04:00'])
    oth = [k for k in wkd if pd.Timestamp(k).weekday() == pd.Timestamp(d).weekday()]
    p = np.median([OCC[k] - NT[k] for k in oth], axis=0) + night; q = two_h(p, y)
    live.append(dict(d=d, dawn=acc(p[H], y[H]), h2=acc(q[H], y[H]), swing=float(np.nanmax(y) - np.nanmin(y))))
L26 = pd.DataFrame(live)
sys.path.insert(0, '../analysis')
with contextlib.redirect_stdout(io.StringIO()): exec(open('../analysis/ahead_2025.py', encoding='utf-8').read().split("out = {}")[0])
R = pd.concat([run_month(m) for m in range(3, 13)]); R = R[R.grp == '월~목']
hol_like = {'2025-10-06', '2025-10-07', '2025-10-08', '2025-10-09', '2025-06-06', '2025-05-05', '2025-05-06', '2025-06-03', '2025-08-15', '2025-10-03'}
R = R[~R.d.isin(hol_like)]  # 월~목 무리에 들어간 공휴일은 '특이사항'이라 뺌
I25 = R.groupby('d').apply(lambda z: pd.Series(dict(dawn=100 * (1 - np.abs(z.none - z.y).sum() / z.y.sum()), h2=100 * (1 - np.abs(z.v0 - z.y).sum() / z.y.sum())))).reset_index()
I26 = pd.DataFrame([dict(d=k, dawn=v['dawn'], h2=v['ahead2h']) for k, v in json.load(open('../analysis/live_recheck_pop_20261123_26.json'))['days'].items()])
def boot_mean(x, n=10000):
    rng = np.random.default_rng(0); m = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(n)]; return np.percentile(m, [2.5, 97.5]), np.percentile(m, [0.5, 99.5])
def t99(x): x = np.asarray(x); h = stats.t.ppf(0.995, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)); return x.mean() - h, x.mean() + h
print('2025 하루 변동폭(30분, 월~목 중앙) %.0f대 | 2026 실시간 %.0f대(11/23~26 중앙) — 잡는 주차장 범위 확인' % (np.median([OCC[d][H].max() - OCC[d][H].min() for d in wkd]), L26.swing.median()))
for name, A, B in (('주차장 안 차량 수', P25, L26), ('공원 인구', I25, I26)):
    print('\n== %s (공연 없는 월~목)' % name)
    for col, lab in (('dawn', '새벽 예상'), ('h2', '2시간 앞')):
        x = A[col].values; c95, c99 = boot_mean(x); p1, p5 = np.percentile(x, [1, 5])
        lo, hi = t99(B[col].values); pct = [stats.percentileofscore(x, v) for v in B[col]]
        print('  %s: 2025 %d일 평균 %.1f%% (95%% %.1f~%.1f, 99%% %.1f~%.1f) | 하루 정확도 1%% 지점 %.1f%%, 5%% 지점 %.1f%%' % (lab, len(x), x.mean(), *c95, *c99, p1, p5))
        print('    2026 실시간 4일: %s → 평균 %.1f%% (99%% 구간 %.1f~%.1f) | 2025 분포에서 위치 %s | 1%% 지점보다 낮은 날 %d개' %
              (', '.join('%s %.1f%%' % (d[5:], v) for d, v in zip(B.d, B[col])), B[col].mean(), lo, hi, ', '.join('%.0f번째' % p for p in pct), int((B[col] < p1).sum())))
        # 2026 평균이 2025 평균과 다른가(0.01): 2025 날 정확도 분포에서 4일 평균의 재표집 분포
        rng = np.random.default_rng(1); sim = np.array([x[rng.integers(0, len(x), len(B))].mean() for _ in range(20000)]); p = 2 * min((sim <= B[col].mean()).mean(), (sim >= B[col].mean()).mean())
        print('    2026 4일 평균이 2025 평일과 다른가: p=%.3f → %s' % (p, '0.01에서 다르다' if p < 0.01 else '0.01에서 다르다고 말할 수 없음'))
