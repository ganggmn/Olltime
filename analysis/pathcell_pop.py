"""길만 있는 250m 칸의 생활인구 확인(2026-11-28).
칸 고르기: analysis/walkgrid/cell250_comp.json(5m 걷는 칸 v3 + OSM 건물·주차장·물·광장을 250m 칸마다 합친 것)에서
  공원 안 98% 이상, 건물 0㎡, 주차장 0㎡, 광장 0㎡인 칸 → 66254675·66504675·66504700·66254700(몽촌토성, 길 15,573㎡, 연못 1,765㎡).
이 네 칸은 2025년 2월 자료에만 있어요(3월부터 서울 생활인구 250m 자료에서 빠짐). 그래서 2025-02 28일로 봄.
공연 저녁: 돔이 걸친 칸(67004650)의 19~21시 평균이 같은 요일 무리 중앙값의 2배 넘는 날.
사용: 맥 data 폴더에서 python3 ../analysis/pathcell_pop.py"""
import glob, numpy as np, pandas as pd
SEL = ['66254675', '66504675', '66504700', '66254700']; DOME = '67004650'
d = pd.read_csv('livingpop_grid/202502.csv', dtype=str, encoding_errors='replace'); d['c'] = d.cell.str[-8:]
d = d[d.c.isin(SEL + [DOME])]; d['v'] = pd.to_numeric(d.total, errors='coerce'); d['h'] = d.hour.astype(int)
P = d.groupby(['date', 'h', 'c']).v.sum().unstack('c').reset_index(); P['wk'] = pd.to_datetime(P.date).dt.weekday >= 5; P['path4'] = P[SEL].sum(1)
ev = P[P.h.between(19, 21)].groupby(['date', 'wk'])[DOME].mean().reset_index(); ev['show'] = ev[DOME] > 2 * ev.groupby('wk')[DOME].transform('median')
S = set(ev[ev.show].date); print('공연 저녁', sorted(S))
a = P[~P.wk & P.date.isin(S)].groupby('h')[['path4', DOME]].mean(); b = P[~P.wk & ~P.date.isin(S)].groupby('h')[['path4', DOME]].mean()
for h in (3, 15, 19, 20, 21, 22): print(f'{h:02d}시 길 4칸 {a.path4[h]:.0f} / {b.path4[h]:.0f} ({a.path4[h]-b.path4[h]:+.0f}) · 돔 칸 {a[DOME][h]:.0f} / {b[DOME][h]:.0f}')
print('새벽 2~4시 4칸 합', round(P[P.h.between(2, 4)].path4.mean()), '· 주말 13~15시', round(P[P.wk & P.h.between(13, 15)].path4.mean()), '· 평일 13~15시', round(P[~P.wk & P.h.between(13, 15)].path4.mean()))
