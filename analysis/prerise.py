"""공연 시작 전 2시간·1시간 증가 모양(2026-11-28 갱민 요청: '2시간 전부터 슬슬, 1시간~40분 전부터 거의 수직').
대상: checks/patterns_2024_2025.csv의 KSPO DOME 공연 날 212일(2024 97, 2025 115).
주차(분 단위 입출차, 사이트와 같은 셈법: 머문 시간 10분~3일, 2025는 북2·동2·남2문)
  - 2025: inout_2025_full.csv. park_show_2h.py처럼 8·9월과 매달 28~31일은 뺌(입출차 기록 빈 구간).
  - 2024: 올림픽공원 입출차 정보_20240731.csv(7월만, 문 구분 없음).
  - 공연 시작 S 기준 −180~+30분 10분 칸마다 주차장 안 차량 수, 10분 증가량.
  - 창 증가율: (S−60 값 − S−120 값)/S−120 값, (S 값 − S−60 값)/S−60 값, (S 값 − S−40 값)/S−40 값.
  - 급증 시작: 그 저녁 10분 증가량 최대의 50%를 처음 넘는 칸(S−180~S+30), 최대 칸.
인원(시간별, 행정동 11710566, livingpop_songpa_2024_2025.csv): 정시 시작 공연만(반 시각 시작은 시간 칸이 어긋나 뺌).
  - KT 시간 칸 h = h:00~h:59. S−2 칸 = 2시간 전~1시간 전, S−1 칸 = 1시간 전~시작.
  - 증가율: 앞 칸 대비 (P(S−2)−P(S−3))/P(S−3), (P(S−1)−P(S−2))/P(S−2), (P(S)−P(S−1))/P(S−1), 사람 수 증가도 같이.
  - 평소 비교: 공연 없는 같은 날 종류(월~목·금·토·일·공휴일, KSPO DOME 공연 날 뺌) 같은 시각 칸 증가율의 중앙값을 공연 날마다 짝지어 뺌.
사용: data 폴더에서 python3 ../analysis/prerise.py → checks/prerise_2024_2025.json(공연별 값, 맥에만), ../analysis/prerise_2024_2025_summary.json(요약)"""
import json, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
P = pd.read_csv('checks/patterns_2024_2025.csv', encoding='utf-8-sig')[['d', '해', '이름', '날종류', '시작', '판매수']]
P['S'] = (P['시작'] * 60).round().astype(int)
# 주차 2025
df = pd.read_csv('inout_2025_full.csv', usecols=['entry_gate', 'entry_time', 'exit_time'], encoding='utf-8-sig')
e = pd.to_datetime(df.entry_time); x = pd.to_datetime(df.exit_time); st = (x - e).dt.total_seconds() / 60
g = df.entry_gate.astype(str).str.split('입구').str[0]; ok = (st >= 10) & (st < 4320) & g.isin(['북2문', '동2문', '남2문'])
E25 = np.sort(e[ok].values); X25 = np.sort(x[ok].values)
d4 = pd.read_csv('한국체육산업개발주식회사_올림픽공원 입출차 정보_20240731.csv', encoding='cp949')
e4 = pd.to_datetime(d4.iloc[:, 1]); x4 = pd.to_datetime(d4.iloc[:, 2]); s4 = (x4 - e4).dt.total_seconds() / 60; k4 = (s4 >= 10) & (s4 < 4320)
E24 = np.sort(e4[k4].values); X24 = np.sort(x4[k4].values)
OFF = np.arange(-180, 31, 10)
def occ(d, S):
    if d.startswith('2025'):
        if d[5:7] in ('08', '09') or d[8:] in ('28', '29', '30', '31'): return None
        E, X = E25, X25
    elif d.startswith('2024-07'): E, X = E24, X24
    else: return None
    t = np.datetime64(d + 'T00:00') + (S + OFF).astype('timedelta64[m]')
    return (np.searchsorted(E, t, 'right') - np.searchsorted(X, t, 'right')).astype(float)
# 인원
L = pd.read_csv('livingpop_songpa_2024_2025.csv', dtype={'date': str, 'hour': str, 'dong': str}, encoding='utf-8-sig')
L = L[L.dong == '11710566']; POP = {(r.date, int(r.hour)): r.total for r in L.itertuples()}
rows = []
for r in P.itertuples():
    d = r.d; S = int(r.S); o = occ(d, S); row = dict(d=d, year=int(r.해), name=r.이름, daytype=r.날종류, start=f'{S // 60:02d}:{S % 60:02d}', sales=int(r.판매수) if pd.notna(r.판매수) else None)
    if o is not None and o[OFF.tolist().index(-120)] > 0:
        v = dict(zip(OFF.tolist(), o)); inc = np.diff(o); mids = OFF[1:]
        m = (mids <= 30); mx = inc[m].max(); i50 = int(np.argmax(inc >= 0.5 * mx)); imx = int(np.argmax(inc))
        row.update(park=dict(occ={str(k): int(v[k]) for k in OFF.tolist()},
            r_120_60=(v[-60] - v[-120]) / v[-120], r_60_0=(v[0] - v[-60]) / v[-60], r_40_0=(v[0] - v[-40]) / v[-40],
            per10_120_60=(v[-60] - v[-120]) / 6, per10_60_0=(v[0] - v[-60]) / 6, per10_40_0=(v[0] - v[-40]) / 4,
            share_last60=(v[0] - v[-60]) / max(1, v[0] - v[-180]), knee50=int(mids[i50]), maxinc_at=int(mids[imx]), maxinc=float(mx)))
    if S % 60 == 0:
        h = S // 60; dd = d.replace('-', ''); p = [POP.get((dd, h + k)) for k in (-3, -2, -1, 0)]
        if all(q is not None for q in p):
            row.update(ppl=dict(h_m3=p[0], h_m2=p[1], h_m1=p[2], h_0=p[3], r_m2=(p[1] - p[0]) / p[0], r_m1=(p[2] - p[1]) / p[1], r_0=(p[3] - p[2]) / p[2], d_m2=p[1] - p[0], d_m1=p[2] - p[1], d_0=p[3] - p[2]))
    rows.append(row)
# 평소(공연 없는 같은 날 종류·같은 시각) 증가율
hol = {r for r in pd.read_csv('holidays.csv', dtype=str).iloc[:, 0]}
def dtype(d):
    wd = pd.Timestamp(d).weekday(); dd = d.replace('-', '')
    return '일·공휴일' if (dd in hol or wd == 6) else '토' if wd == 5 else '금' if wd == 4 else '월~목'
showd = {r['d'] for r in rows}; NS = {}
for d in [x.strftime('%Y-%m-%d') for x in pd.date_range('2024-01-01', '2025-12-31')]:
    if d not in showd: NS.setdefault(dtype(d), []).append(d.replace('-', ''))
def base_rate(pool, a, b):
    v = [(POP[(x, b)] - POP[(x, a)]) / POP[(x, a)] for x in pool if (x, a) in POP and (x, b) in POP]
    return float(np.median(v)) if v else None
for r in rows:
    if 'ppl' not in r: continue
    h = int(r['start'][:2]); pool = NS.get(dtype(r['d']), [])
    b2, b1, b0 = base_rate(pool, h - 3, h - 2), base_rate(pool, h - 2, h - 1), base_rate(pool, h - 1, h)
    r['ppl'].update(base_m2=b2, base_m1=b1, base_0=b0, ex_m2=r['ppl']['r_m2'] - b2, ex_m1=r['ppl']['r_m1'] - b1, ex_0=r['ppl']['r_0'] - b0)
def dist(a):
    a = np.array([q for q in a if q is not None and np.isfinite(q)], float)
    if not len(a): return None
    return dict(n=int(len(a)), min=float(a.min()), p10=float(np.percentile(a, 10)), median=float(np.median(a)), p90=float(np.percentile(a, 90)), max=float(a.max()))
pk = [r['park'] for r in rows if 'park' in r]; pp = [r['ppl'] for r in rows if 'ppl' in r]
out = dict(made='2026-11-28', days=len(rows), park_days=len(pk), ppl_days=len(pp),
    park={k: dist([q[k] for q in pk]) for k in ['r_120_60', 'r_60_0', 'r_40_0', 'per10_120_60', 'per10_60_0', 'per10_40_0', 'share_last60', 'knee50', 'maxinc_at']},
    park_profile={str(o): dist([q['occ'][str(o)] - q['occ']['-180'] for q in pk]) for o in OFF.tolist()},
    park_inc10={str(o): dist([q['occ'][str(o)] - q['occ'][str(o - 10)] for q in pk]) for o in OFF.tolist()[1:]},
    ppl={k: dist([q[k] for q in pp]) for k in ['r_m2', 'r_m1', 'r_0', 'd_m2', 'd_m1', 'd_0', 'base_m2', 'base_m1', 'base_0', 'ex_m2', 'ex_m1', 'ex_0']},
    ppl_above_base=dict(m2=sum(q['ex_m2'] > 0 for q in pp), m1=sum(q['ex_m1'] > 0 for q in pp), n=len(pp)),
    park_full_by_m60=sum(q['occ']['-60'] >= 0.95 * max(q['occ'].values()) for q in pk),
    by_year={str(y): dict(park={k: dist([r['park'][k] for r in rows if 'park' in r and r['year'] == y]) for k in ['r_120_60', 'r_60_0', 'knee50']},
                          ppl={k: dist([r['ppl'][k] for r in rows if 'ppl' in r and r['year'] == y]) for k in ['r_m2', 'r_m1', 'r_0']}) for y in (2024, 2025)},
    rows=rows)
json.dump(out, open('checks/prerise_2024_2025.json', 'w'), ensure_ascii=False, indent=1, default=float)
sm = {k: v for k, v in out.items() if k != 'rows'}; sm['source'] = '주차: 한국체육산업개발 올림픽공원 입출차(2024-07, 2025) · 인원: 서울특별시 공공데이터 생활인구(행정동 11710566) · 공연 날: patterns_2024_2025.csv'
json.dump(sm, open('../analysis/prerise_2024_2025_summary.json', 'w'), ensure_ascii=False, indent=1, default=float)
f = lambda D, pct=False: '없음' if D is None else (f"n {D['n']} | 최소 {D['min']*100:.1f}% · 10% {D['p10']*100:.1f}% · 중앙 {D['median']*100:.1f}% · 90% {D['p90']*100:.1f}% · 최대 {D['max']*100:.1f}%" if pct else f"n {D['n']} | 최소 {D['min']:.0f} · 10% {D['p10']:.0f} · 중앙 {D['median']:.0f} · 90% {D['p90']:.0f} · 최대 {D['max']:.0f}")
print('공연 날', len(rows), '주차 있는 날', len(pk), '인원(정시 시작)', len(pp))
for k in ['r_120_60', 'r_60_0', 'r_40_0', 'share_last60']: print('주차', k, f(out['park'][k], True))
for k in ['per10_120_60', 'per10_60_0', 'per10_40_0', 'knee50', 'maxinc_at']: print('주차', k, f(out['park'][k]))
for k in ['r_m2', 'r_m1', 'r_0', 'base_m2', 'base_m1', 'base_0', 'ex_m2', 'ex_m1', 'ex_0']: print('인원', k, f(out['ppl'][k], True))
print('평소보다 큼', out['ppl_above_base'], '1시간 전 이미 최대의 95%', out['park_full_by_m60'], '/', len(pk))
for k in ['d_m2', 'd_m1', 'd_0']: print('인원', k, f(out['ppl'][k]))
print('10분 증가 중앙(시작 기준 분: 대수)', {k: round(v['median']) for k, v in out['park_inc10'].items()})
for y in ('2024', '2025'): print(y, {k: (None if v is None else (v['n'], round(v['median'] * (1 if k == 'knee50' else 100), 1))) for k, v in {**out['by_year'][y]['park'], **out['by_year'][y]['ppl']}.items()})
