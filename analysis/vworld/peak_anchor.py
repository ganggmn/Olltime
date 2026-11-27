"""피크 예측이 안 좋아진 까닭 나누기: 모양 문제인가, 기준점(언제를 0으로 두나) 문제인가.
기준점 세 가지로 '사람 모양'(공원 인구 5분 감소, 평균)을 배우고 오늘 저녁에 적용:
  P 주차 출차 시작(공연 중 실제로 알 수 있음) / E 진짜 끝(현실에선 모름, 상한) / K 그 저녁 공원 인구 감소 정점(현실에선 30분 늦게 앎, 상한)"""
import os, numpy as np, pandas as pd
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apply_model.py'), encoding='utf-8').read()
exec(src.split("K = np.arange(6, 36)")[0])
K = np.arange(6, 36); acc = lambda p, t: 100 * (1 - np.abs(p[K] - t[K]).sum() / max(t[K].sum(), 1))
TAUS = np.arange(-60, 120, 5)
def drop_abs(o): return np.clip(-np.diff(o['pop5']), 0, None)  # 칸 i: [5i, 5i+5) 동안 줄어든 인구
def pop_peak(o):
    d = drop_abs(o); lo, hi = (o['st'] + 40) // 5, (o['st'] + 360) // 5; sm = np.convolve(d, [1, 2, 1], 'same'); return int(lo + np.argmax(sm[lo:hi])) * 5
def shape_at(o, a):
    b0 = int(a - 60) // 5; d = drop_abs(o)[b0: b0 + len(TAUS)]; return d / d.sum() if d.sum() > 0 else d
anch = {'P': lambda o, t: o['st'] + onset_of(o), 'E': lambda o, t: t['end'], 'K': lambda o, t: pop_peak(o)}
pp = np.array([pop_peak(o) for o, _ in HIST]); po = np.array([o['st'] + on for (o, _), on in zip(HIST, ON)]); te = np.array([t['end'] for _, t in HIST])
q = lambda x: '중앙 %+.0f분, 10~90%% %+.0f ~ %+.0f분' % (np.median(x), *np.percentile(x, [10, 90]))
print('과거 40저녁: 공원 인구 감소 정점 − 진짜 끝: %s | 정점 − 주차 출차 시작: %s | 주차 출차 시작 − 진짜 끝: %s' % (q(pp - te), q(pp - po), q(po - te)))
SH = {k: np.mean(np.vstack([shape_at(o, f(o, t)) for o, t in HIST]), axis=0) for k, f in anch.items()}
for k in SH: SH[k] /= SH[k].sum(); print('  기준 %s 사람 모양: 가장 많이 빠지는 5분 %+d분, 10·50·90%% 빠지는 때 %s' % (k, TAUS[np.argmax(SH[k])], ', '.join('%+d' % TAUS[np.searchsorted(np.cumsum(SH[k]), x)] for x in (.1, .5, .9))))
def s2pred(o, a, sh, vol):
    f = np.zeros(2000)
    for tau, s in zip(TAUS, sh): f[int(a + tau): int(a + tau) + 5] += vol * s / 5
    return np.array([f[o['st'] + 10 * k: o['st'] + 10 * k + 10].sum() for k in range(NS_)])
rows = []
for SET, nm in ((TEST, '같은 세계 100'), (STRESS, '가정 깨기 30')):
    for i, (o, t) in enumerate(SET):
        pk_t = int(np.argmax(t['s2_in']))
        for k, f in anch.items():
            p = s2pred(o, f(o, t), SH[k], VOL * o['N']); rows.append(dict(set=nm, i=i, how=k, s2=acc(p, t['s2_in']), hit=int(np.argmax(p) == pk_t), near=int(abs(np.argmax(p) - pk_t) <= 1), err=float(f(o, t) - (pop_peak(o) if k == 'K' else t['end']))))
        p = predict(o, 'D 실제 끝 안다면(그날 주차)')['s2']; rows.append(dict(set=nm, i=i, how='D(앞 결과, 주차 모양)', s2=acc(p, t['s2_in']), hit=int(np.argmax(p) == pk_t), near=int(abs(np.argmax(p) - pk_t) <= 1)))
R = pd.DataFrame(rows)
for nm, x in R.groupby('set', sort=False):
    print('\n== %s저녁: S2 10분 정확도 / 최고 칸 맞힘 / ±10분' % nm)
    lab = {'P': 'P 주차 출차 시작 기준 + 인구 모양(공연 중 가능)', 'E': 'E 진짜 끝 기준 + 인구 모양(현실에선 모름)', 'K': 'K 그날 인구 정점 기준 + 인구 모양(30분 늦게 앎)', 'D(앞 결과, 주차 모양)': 'D 앞 결과(주차 출차 시작 + 주차 모양)'}
    for k in ('D(앞 결과, 주차 모양)', 'P', 'E', 'K'):
        y = x[x.how == k]; print('  %-44s %6.1f%%  %4.0f%%  %4.0f%%' % (lab[k], y.s2.mean(), 100 * y.hit.mean(), 100 * y.near.mean()))
R.to_csv('checks/vworld/peak_anchor.csv', index=False)
