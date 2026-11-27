"""날 종류별 정확도(2026-11-27): 주차장 안 차량 수(ladder.py 예측, 한 달씩 숨김)와 공원 인구(ahead_2025.py, 앞선 달로만 배움). 하루 전·새벽 예상과 2시간 앞, 하위 10% 날, 시간 오차 90% 지점.
사용: data 폴더에서 python3 ../analysis/accuracy_bytype.py"""
import io, contextlib, os, sys, pickle, numpy as np, pandas as pd
sys.argv = ['ladder.py']
with contextlib.redirect_stdout(io.StringIO()): exec(open('../analysis/ladder.py', encoding='utf-8').read())
SHOW = pickle.load(open(os.path.expanduser('~/past3.pkl'), 'rb'))['show']
r = pd.Series(y - P, index=D.index); prev = r.reindex(D.index - pd.Timedelta(hours=2)).values; Q2 = np.where(np.isnan(prev), P, np.maximum(P + prev, 0))
dv = D.date.values; dow = D.dow.values
big = np.array([bool(SHOW.get(str(d)[:10], {}).get('big')) for d in dv]); anyshow = np.array([bool(SHOW.get(str(d)[:10])) for d in dv])
hol_ = np.array([(d in hol) for d in dv]) | np.isin(dv, list(MJ))
grp = np.select([~anyshow & ~hol_ & (dow < 4), ~anyshow & ~hol_ & (dow == 4), ~anyshow & (hol_ | (dow >= 5)), big], ['월~목 공연 없음', '금 공연 없음', '주말·공휴일 공연 없음', '큰 공연 날'], '작은 공연만 있는 날')
print('주차장 안 차량 수(2025, 한 달씩 숨기고 맞힘, 07~23시, 채점 달 %s)' % EV)
print('  %-18s %4s %10s %10s %14s %14s' % ('날 종류', '날수', '하루 전 예상', '2시간 앞', '하루 정확도 하위10%', '시간 오차 90% 지점'))
for g in ['월~목 공연 없음', '금 공연 없음', '주말·공휴일 공연 없음', '작은 공연만 있는 날', '큰 공연 날']:
    mk = day & np.isin(D.m.values, EV) & ~np.isnan(P) & (grp == g)
    if not mk.any(): continue
    a1 = 100 * (1 - np.abs(P - y)[mk].sum() / y[mk].sum()); a2 = 100 * (1 - np.abs(Q2 - y)[mk].sum() / y[mk].sum())
    dd_ = pd.DataFrame(dict(d=dv[mk], e=np.abs(Q2 - y)[mk], y=y[mk])).groupby('d').apply(lambda z: 100 * (1 - z.e.sum() / z.y.sum()))
    ape = np.abs(Q2 - y)[mk] / np.maximum(y[mk], 1) * 100
    print('  %-18s %4d %9.1f%% %9.1f%% %13.1f%% %13.1f%%' % (g, len(set(dv[mk])), a1, a2, np.percentile(dd_, 10), np.percentile(ape, 90)))
sys.path.insert(0, '../analysis'); src2 = open('../analysis/ahead_2025.py', encoding='utf-8').read().split("out = {}")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src2)
R = pd.concat([run_month(m) for m in range(3, 13)])
print('\n공원 인구(2025 생활인구 POI, KT, 07~23시, 3~12월, 앞선 달로만 배움)')
print('  %-10s %4s %10s %10s %14s %14s' % ('날 종류', '날수', '새벽 예상', '2시간 앞', '하루 정확도 하위10%', '시간 오차 90% 지점'))
for g, x in R.groupby('grp'):
    dayacc = x.groupby('d').apply(lambda z: 100 * (1 - np.abs(z.v2 - z.y).sum() / z.y.sum())); ape = np.abs(x.v2 - x.y) / x.y * 100
    print('  %-10s %4d %9.1f%% %9.1f%% %13.1f%% %13.1f%%' % (g, x.d.nunique(), acc(x, 'none'), acc(x, 'v2'), np.percentile(dayacc, 10), np.percentile(ape, 90)))
x = R[R.grp == '월~목']; worst = x.groupby('d').apply(lambda z: 100 * (1 - np.abs(z.v2 - z.y).sum() / z.y.sum())).sort_values().head(6)
print('  월~목 중 가장 안 맞은 날(공휴일 포함):', ', '.join('%s %.0f%%' % (d, v) for d, v in worst.items()))
