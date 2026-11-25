"""공연 날 버스와 따릉이가 관객을 얼마나 실어 나르나(2025년, 공원 둘레). 표준 라이브러리 + pandas.
사용: python3 analysis/transit_2025.py  (bus_park_2025.csv.gz, bike_park_2025.csv.gz, shows_site_2024-12_2025-12.json 필요. 받는 법은 scripts/fetch_transit_2025.py)
- 버스: 공원 둘레 16개 정류장의 하루 승차·하차 합을, 같은 요일·앞뒤 5주 안의 KSPO DOME 공연 없는 날 중앙값과 견줌
- 따릉이: 공연 시작 2~4시간 뒤 공원 대여소에서 빌려 공원 밖 대여소에 반납한 수를, 같은 요일 다른 날과 견줌"""
import pandas as pd, json, os
H = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(H, 'shows_site_2024-12_2025-12.json'), encoding='utf-8')); dome = {}
for s in S['list']:
    if s['venue'] == 'KSPO DOME' and s['d'].startswith('2025'): dome.setdefault(s['d'], s)
B = pd.read_csv(os.path.join(H, 'bus_park_2025.csv.gz'), dtype=str)
for c in ('on', 'off'): B[c] = pd.to_numeric(B[c], errors='coerce')
B['d'] = pd.to_datetime(B.date, format='%Y%m%d'); day = B.groupby('d')[['on', 'off']].sum(); day['wd'] = day.index.weekday
day['dome'] = [d.strftime('%Y-%m-%d') in dome for d in day.index]
rows = []
for d, r in day[day.dome].iterrows():
    base = day[(~day.dome) & (day.wd == r.wd) & (abs(day.index - d) <= pd.Timedelta(days=35))]
    if len(base) >= 2: rows.append(dict(d=d.strftime('%Y-%m-%d'), wd='월화수목금토일'[r.wd], name=dome[d.strftime('%Y-%m-%d')]['short'][:12], on_ex=int(r.on - base.on.median()), off_ex=int(r.off - base.off.median())))
R = pd.DataFrame(rows)
print('버스(공원 둘레 16개 정류장): 하루 평균 승차 %d, 하차 %d' % (day.on.mean(), day.off.mean()))
print('  큰 공연 날 늘어난 승차 중앙값 %d명(하차 %d명), 요일별:' % (R.on_ex.median(), R.off_ex.median()), R.groupby('wd').on_ex.median().astype(int).to_dict())
print('  가장 많이 는 날:', R.sort_values('on_ex').tail(3)[['d', 'name', 'on_ex']].values.tolist())
print('  줄어든 날(대부분 공휴일·연휴):', R.sort_values('on_ex').head(3)[['d', 'name', 'on_ex']].values.tolist())
K = pd.read_csv(os.path.join(H, 'bike_park_2025.csv.gz'), dtype=str); K['rt'] = pd.to_datetime(K.rent_time, errors='coerce')
P = {'1268', '1267', '2622', '2621', '4857', '5781', '5751', '4862', '4481', '4865', '4464', '4856'}
K['out'] = K.rent_station.isin(P) & ~K.return_station.isin(P); K['d'] = K.rt.dt.strftime('%Y-%m-%d'); K['h'] = K.rt.dt.hour
rows = []
for d, s in dome.items():
    h0 = int(s['t'][:2]); dd = pd.Timestamp(d); sel = lambda x: int(((x.h >= h0 + 2) & (x.h < h0 + 4) & x.out).sum())
    base = [sel(K[K.d == b.strftime('%Y-%m-%d')]) for b in pd.date_range(dd - pd.Timedelta(days=35), dd + pd.Timedelta(days=35)) if b.weekday() == dd.weekday() and b.strftime('%Y-%m-%d') not in dome]
    if base: rows.append((sel(K[K.d == d]), sorted(base)[len(base) // 2]))
X = pd.DataFrame(rows, columns=['after', 'base']); X['ex'] = X.after - X.base
print('따릉이(공원 둘레 12개 대여소, 2025년 %d건): 공연 끝난 뒤 2시간 동안 공원에서 빌려 나간 수 중앙값 %d(평소 %d), 늘어난 수 중앙값 %d, 최대 %d' % (len(K), X.after.median(), X.base.median(), X.ex.median(), X.ex.max()))
