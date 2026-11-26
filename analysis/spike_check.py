"""서울시 실시간 인구에서 '5분 한 번만 튀었다 돌아온 값'이 얼마나 자주 나오는지 봐요(탐색).
- 실시간: 맥이 모은 data/citydata/raw_*.jsonl.gz(2026-11-22~). 앞뒤가 서로 비슷한데 가운데 하나만 기준 이상 높거나 낮은 값.
- 매일 18:05: 17:50~18:20 값을 날마다 보여 줌.
- 2025년: 5분 실시간 과거 자료는 서울시가 쌓아 두지 않아 없음. 대신 시간별 생활인구(POI127)에서 한 시간만 튄 값을 셈.
사용: data 폴더에서 python3 ../analysis/spike_check.py → checks/spike_check.json"""
import gzip, json, glob, pandas as pd, numpy as np
rows = []
for f in sorted(glob.glob('citydata/raw_*.jsonl.gz')):
    for line in gzip.open(f, 'rt', encoding='utf-8'):
        try: p = json.loads(line)['response']['CITYDATA']['LIVE_PPLTN_STTS'][0]
        except Exception: continue
        rows.append((pd.Timestamp(p['PPLTN_TIME']), float(p['AREA_PPLTN_MIN']), float(p['AREA_PPLTN_MAX']), p.get('AREA_CONGEST_LVL'), p.get('MALE_PPLTN_RATE')))
B = pd.DataFrame(rows, columns=['t', 'lo', 'hi', 'lvl', 'male']).drop_duplicates('t').sort_values('t').reset_index(drop=True); B['m'] = (B.lo + B.hi) / 2
pv, nx = B.m.shift(1), B.m.shift(-1); ok = (B.t.diff() == pd.Timedelta('5min')) & (B.t.shift(-1) - B.t == pd.Timedelta('5min'))
out = dict(readings=len(B), first=str(B.t.min()), last=str(B.t.max()), realtime={})
print('실시간 %d개(%s ~ %s)' % (len(B), B.t.min(), B.t.max()))
for th in [1000, 2000, 3000]:
    up = ok & (B.m - np.maximum(pv, nx) >= th) & ((pv - nx).abs() <= th / 2); dn = ok & (np.minimum(pv, nx) - B.m >= th) & ((pv - nx).abs() <= th / 2)
    ts = [str(t)[5:16] for t in B.t[up | dn]]; print('  한 번만 %d명 이상: 위 %d, 아래 %d %s' % (th, up.sum(), dn.sum(), ts)); out['realtime'][th] = dict(up=int(up.sum()), down=int(dn.sum()), at=ts)
r16 = (B.m / np.maximum(pv, nx) > 1.6) & ok; print('  앞뒤의 1.6배 넘게 혼자 튄 값(사이트가 기록에서 빼는 기준): %d개' % r16.sum())
mx = (B.m / pv)[(B.t.diff() == pd.Timedelta('5min')) & ~r16]; im = mx.idxmax()
print('  그 값을 빼면 5분 사이 가장 큰 오름: %.2f배(%s, %d → %d)' % (mx.max(), B.t[im], pv[im], B.m[im])); out['max_5min_rise_excl'] = round(float(mx.max()), 3)
out['at_1805'] = {}
for d in sorted(set(B.t.dt.strftime('%Y-%m-%d'))):
    w = B[(B.t >= d + ' 18:00') & (B.t <= d + ' 18:10')].m
    if len(w) == 3: print('  %s 18:00 %d → 18:05 %d → 18:10 %d' % (d, *w.values)); out['at_1805'][d] = [float(v) for v in w.values]
PO = pd.read_csv('checks/park_population_2025_hourly_poi127_full.csv').sort_values('ts').reset_index(drop=True); y = PO.park_pop; pv, nx = y.shift(1), y.shift(-1)
sim = (pv - nx).abs() <= 0.15 * np.maximum(pv, nx)
for r in [1.3, 1.5]:
    n = int(((y >= r * np.maximum(pv, nx)) & sim).sum() + ((y * r <= np.minimum(pv, nx)) & sim).sum()); print('2025 시간별 %d시간: 한 시간만 앞뒤의 %.1f배 이상(위·아래) %d개' % (len(PO), r, n)); out['h2025_%s' % r] = n
top = PO.assign(j=y - np.maximum(pv, nx))[sim].nlargest(5, 'j'); print('  가장 크게 혼자 오른 시간:', ', '.join('%s +%d' % (t[:13], j) for t, j in zip(top.ts, top.j)))
out['h2025_top'] = [(t, round(float(j))) for t, j in zip(top.ts, top.j)]
json.dump(out, open('checks/spike_check.json', 'w'), ensure_ascii=False, indent=1)
