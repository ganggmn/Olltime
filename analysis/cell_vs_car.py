"""사람 수 예상: '차 대수 × 차 한 대당 방문객 수'(예전) vs '기지국 인구 모양'(지금)을 2025년 1년으로 같은 조건에서 견줘요.
정답: 서울 생활인구를 서울시 '올림픽공원' 구역에 맞춰 더한 시간별 값(checks/park_population_2025_hourly_poi127.csv).
두 방법 모두 그날 새벽(3~4시) 사람 수를 바닥으로 쓰고, 배우는 값(차 한 대당 방문객 수, 시간대 모양)은 그 달을 빼고 구해요(한 달씩 숨기기).
- 차 방법: 바닥 + (날 종류×시각별 '방문객 ÷ 차' 중앙값) × (그 시각 주차 예상 − 새벽 주차). 주차 예상은 ladder.py의 내일 예측.
- 기지국 방법: 바닥 + (날 종류×시각별 사람 수 모양 중앙값).
- 2시간 앞: 두 방법 모두 2시간 전 실제 사람 수와의 차이를 남는 비율만큼 더함(차 방법은 주차 예상도 2시간 전 실제 주차로 고침).
사용: data 폴더에서 python3 ../analysis/cell_vs_car.py"""
import os, io, contextlib, json, numpy as np, pandas as pd
src = open(os.path.join('..', 'analysis', 'ladder.py'), encoding='utf-8').read(); src = src[:src.index("print('모드'")]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
P = ladder('dt1', 1, 1)
S = json.load(open('checks/shows_site_2024-12_2025-12.json', encoding='utf-8')); DOMED = {s['d'] for s in S['list'] if s['venue'] == 'KSPO DOME'}
pop = pd.read_csv('checks/park_population_2025_hourly_poi127.csv', encoding='utf-8-sig'); pop['t'] = pd.to_datetime(pop.ts); pop = pop.set_index('t').park_pop
D['pop'] = pop.reindex(D.index).values; D['car'] = y; D['Pc'] = P
dv = D.date.values; dow = D.dow.values; hl = np.array([d in hol for d in dv])
base = np.select([hl | (dow == 6), dow == 5, dow == 4], ['hol', 'sat', 'fri'], 'wk'); show = np.isin(dv, list(DOMED))
D['k'] = np.where(show & (base != 'wk'), np.char.add(base.astype(str), '_show'), base)
nt = D[D.h.isin([3, 4])].groupby('date').agg(pn=('pop', 'median'), cn=('car', 'median')); D = D.join(nt, on='date')
D['px'] = D['pop'] - D.pn; D['cx'] = (D.car - D.cn).clip(lower=0); D['ratio'] = np.where(D.cx > 100, D.px / D.cx.where(D.cx > 100), np.nan)
ok = D['pop'].notna() & D.pn.notna()
fc_cell = np.full(len(D), np.nan); fc_car = np.full(len(D), np.nan)
for m in MONTHS:
    te = (D.m.values == m); tr = ~te & ok.values
    if tr.sum() < 500: continue
    T = D[tr]; prof = T.groupby(['k', 'h']).px.median(); kc = T[T.h.between(7, 23)].groupby(['k', 'h']).ratio.median()
    kc0 = T.groupby('h').ratio.median()
    idx = pd.MultiIndex.from_arrays([D.k, D.h])
    pr = prof.reindex(idx).values; kk = kc.reindex(idx).values; kk = np.where(np.isnan(kk), kc0.reindex(D.h).values, kk)
    fc_cell[te] = (D.pn.values + pr)[te]
    fc_car[te] = (D.pn.values + np.nan_to_num(kk) * np.maximum(0, D.Pc.values - D.cn.values))[te]
D['fcell'] = fc_cell; D['fcar'] = fc_car
# 2시간 앞
B_NS, B_SH = 0.89, 0.82; BC_NS, BC_SH = 0.88, 0.85
sh = D.k.str.endswith('_show').values; bp = np.where(sh, B_SH, B_NS); bc = np.where(sh, BC_SH, BC_NS)
lag = lambda s: pd.Series(s, index=D.index).reindex(D.index - pd.Timedelta(hours=2)).values
pop2 = lag(D['pop'].values); cell2 = lag(fc_cell); car2a = lag(D.car.values); pc2 = lag(D.Pc.values); fcar2 = lag(fc_car)
D['g_cell'] = np.where(np.isnan(pop2) | np.isnan(cell2), fc_cell, fc_cell + bp * (pop2 - cell2))
# 차 방법 2시간: 주차 예상을 2시간 전 실제 주차로 고친 뒤 계수를 곱하고, 사람 수 차이도 더함
Pc_corr = np.where(np.isnan(car2a), D.Pc.values, D.Pc.values + bc * (car2a - pc2))
idx = pd.MultiIndex.from_arrays([D.k, D.h])
D['g_car'] = np.nan
for m in MONTHS:
    te = (D.m.values == m); tr = ~te & ok.values
    if tr.sum() < 500: continue
    T = D[tr]; kc = T[T.h.between(7, 23)].groupby(['k', 'h']).ratio.median(); kc0 = T.groupby('h').ratio.median()
    kk = kc.reindex(idx).values; kk = np.where(np.isnan(kk), kc0.reindex(D.h).values, kk)
    shape = D.pn.values + np.nan_to_num(kk) * np.maximum(0, Pc_corr - D.cn.values)
    shape2 = lag(D.pn.values + np.nan_to_num(kk) * np.maximum(0, D.Pc.values - D.cn.values))
    g = np.where(np.isnan(pop2) | np.isnan(shape2), shape, shape + bp * (pop2 - shape2))
    D.loc[te, 'g_car'] = g[te]
ev = D.h.between(7, 23).values & np.isin(D.m.values, EV) & ok.values & ~np.isnan(fc_car) & ~np.isnan(fc_cell)
kind = np.select([np.isin(dv, list(MJ)), hl & (dow < 5), show & (dow >= 4), dow == 6, dow == 5, dow == 4], ['설·추석', '평일 공휴일', '큰 공연 날(금·토·일)', '일요일', '토요일', '금요일'], '월~목')
def acc(col, mk):
    a = D['pop'].values[mk]; f = D[col].values[mk]; g = ~np.isnan(f) & ~np.isnan(a); e = np.abs(f[g] - a[g])
    return 100 * (1 - e.sum() / a[g].sum()), e.mean()
print('정답: 서울 생활인구(올림픽공원 구역). 07~23시, 1~7월·10월. 정확도(평균 오차)')
print('%-20s %5s | %-17s %-17s | %-17s %-17s' % ('날', '시간', '내일: 차 방법', '내일: 기지국 방법', '2시간 앞: 차', '2시간 앞: 기지국'))
for k in ['월~목', '금요일', '토요일', '일요일', '큰 공연 날(금·토·일)', '평일 공휴일', '설·추석', '전체']:
    mk = ev & (kind == k) if k != '전체' else ev
    if mk.sum() == 0: continue
    r = [acc(c, mk) for c in ('fcar', 'fcell', 'g_car', 'g_cell')]
    print('%-20s %5d | %5.1f%% (%5.0f명)  %5.1f%% (%5.0f명)  | %5.1f%% (%5.0f명)  %5.1f%% (%5.0f명)' % (k, mk.sum(), *[v for t in r for v in t]))
# 주차 예상이 틀린 만큼 사람 수가 따라 틀리는지(연쇄): 주차 예상 오차와 사람 수 예상 오차의 상관
ce = (D.Pc - D.car).values; pe_car = (D.fcar - D['pop']).values; pe_cell = (D.fcell - D['pop']).values; mk = ev & ~np.isnan(ce)
print('\n주차 예상 오차와 사람 수 예상 오차의 상관: 차 방법 %+.2f, 기지국 방법 %+.2f' % (np.corrcoef(ce[mk], pe_car[mk])[0, 1], np.corrcoef(ce[mk], pe_cell[mk])[0, 1]))
