"""공원에서 가장 가까운 서울시 교통량 지점(2.2~4km, 차량 검지기, 시간별)에서 KSPO DOME 공연 날 차가 늘어나는지 봐요.
사용: python3 analysis/topis_shows.py (analysis/topis_2025.csv.gz, topis_spots.json, shows_site_2024-12_2025-12.json)
기준: 같은 요일, 앞뒤 9주 안의 KSPO DOME 공연 없는 날(공휴일 뺌) 같은 시각 중앙값."""
import json, numpy as np, pandas as pd
T = pd.read_csv('analysis/topis_2025.csv.gz', dtype={'일자': str}); S = json.load(open('analysis/topis_spots.json', encoding='utf-8'))
hc = ['%d시' % h for h in range(24)]
for c in hc: T[c] = pd.to_numeric(T[c], errors='coerce')
SH = json.load(open('analysis/shows_site_2024-12_2025-12.json', encoding='utf-8'))
dome = {}
for s in SH['list']:
    if s['venue'] == 'KSPO DOME' and s['d'].startswith('2025'): dome.setdefault(s['d'].replace('-', ''), s)
HOL = {'20250101', '20250127', '20250128', '20250129', '20250130', '20250303', '20250505', '20250506', '20250603', '20250606', '20250815', '20251003', '20251006', '20251007', '20251008', '20251009', '20251225'}
T['wd'] = pd.to_datetime(T['일자']).dt.weekday; T['key'] = T['지점번호'] + '|' + T['방향'] + '|' + T['구분'].astype(str)
rows = []
for d, s in dome.items():
    if d in HOL: continue
    st = int(s['t'][:2]); en = st + int(np.ceil(((s.get('run') or 150) + 15) / 60)); wd = pd.Timestamp(d).weekday()
    base = [b for b in T['일자'].unique() if b not in dome and b not in HOL and pd.Timestamp(b).weekday() == wd and abs((pd.Timestamp(b) - pd.Timestamp(d)).days) <= 63]
    if len(base) < 2: continue
    for key, g in T[T['일자'].isin([d] + base)].groupby('key'):
        cur = g[g['일자'] == d]
        if cur.empty: continue
        b = g[g['일자'].isin(base)][hc].median()
        for lab, hs in (('시작 전 2시간', range(st - 2, st)), ('끝난 뒤 2시간', range(en, min(en + 2, 24)))):
            vv = cur[[hc[h] for h in hs]].iloc[0]
            if vv.isna().any() or (vv <= 0).any(): continue
            v = vv.sum(); bb = sum(b[hc[h]] for h in hs)
            if np.isnan(v) or np.isnan(bb) or bb <= 0: continue
            rows.append(dict(d=d, key=key, ph=lab, ex=v - bb, pct=100 * (v - bb) / bb, wkend=wd >= 5))
R = pd.DataFrame(rows)
print('KSPO DOME 공연 날 %d일, 지점·방향 %d개' % (R.d.nunique(), R.key.nunique()))
Q = R.groupby(['key', 'ph']).agg(n=('ex', 'size'), ex=('ex', 'median'), pct=('pct', 'median'), pos=('ex', lambda x: (x > 0).mean() * 100)).reset_index()
Q['m'] = Q.key.str.split('|').str[0].map(lambda k: S.get(k, {}).get('m'))
print(Q[Q.n >= 8].sort_values(['ph', 'pct'], ascending=[True, False]).round(1).to_string(index=False))
Q.to_csv('analysis/topis_shows_2025.csv', index=False, encoding='utf-8-sig')
