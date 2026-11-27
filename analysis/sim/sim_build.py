"""과거 공연 저녁 시뮬레이션 입력: 정답(시간별 공원 인구), 출차 알림(새 규칙)·혼잡 정답.
2025: 정답 = 서울 생활인구 '올림픽공원' 구역 합(poi127). 2024: 공원 값이 없어 동 11710566 값 − (2025 공연 없는 날의 동−공원 차이, 날 종류×시각 중앙값).
출차: 2025 입출차(CMB 제외), 2024는 7월만 있음. 새 규칙 = 10분 순유출 120대(2025 단위) 두 번 연속, 예전 = 10분 6.5% 주차 대수 감소."""
import os, json, pickle, numpy as np, pandas as pd
os.chdir(os.path.expanduser('~/mnt/(주)한국체육산업개발 공모전/data'))
HOL = {r[:4] + '-' + r[4:6] + '-' + r[6:] for r in pd.read_csv('holidays.csv', dtype=str).iloc[:, 0]}
P = pickle.load(open(os.path.expanduser('~/past3.pkl'), 'rb')); SHOW = P['show']
hm = lambda t: int(t[:2]) * 60 + int(t[3:5])
dtk = lambda s: 'hol' if (pd.Timestamp(s).weekday() == 6 or s in HOL) else 'sat' if pd.Timestamp(s).weekday() == 5 else 'fri' if pd.Timestamp(s).weekday() == 4 else 'wk'
park = pd.read_csv('checks/park_population_2025_hourly_poi127.csv', encoding='utf-8-sig'); park['ts'] = pd.to_datetime(park.ts); park = park.set_index('ts').park_pop
d = pd.read_csv('livingpop_songpa_2024_2025.csv', encoding='utf-8-sig', dtype={'dong': str, 'date': str, 'hour': str})
d = d[d.dong == '11710566']; d['ts'] = pd.to_datetime(d.date + d.hour, format='%Y%m%d%H'); dong = d.set_index('ts').total.sort_index()
show25 = {k for k, v in SHOW.items() if any('KSPO' in b['venue'] for b in v.get('big', []))}
J = pd.DataFrame({'dong': dong, 'park': park}).dropna(); J['day'] = J.index.strftime('%Y-%m-%d'); J['k'] = [dtk(s) for s in J.day]; J['h'] = J.index.hour
J0 = J[~J.day.isin(show25)]; OFF = (J0.dong - J0.park).groupby([J0.k, J0.h]).median()
def truth_day(day):
    t0 = pd.Timestamp(day); idx = pd.date_range(t0, periods=24, freq='h')
    if day.startswith('2025'):
        v = park.reindex(idx).values
    else:
        k = dtk(day); v = dong.reindex(idx).values - np.array([OFF[(k, h)] for h in range(24)])
    return None if np.isnan(v).any() else [round(float(x), 1) for x in v]
# 출차
def io25():
    df = pd.read_csv('inout_2025_full.csv', usecols=['entry_gate', 'entry_time', 'exit_time'], encoding='utf-8-sig')
    a = df[~df.entry_gate.str.contains('CMB')]
    return pd.to_datetime(a.entry_time, errors='coerce'), pd.to_datetime(a.exit_time, errors='coerce'), pd.to_datetime(df.entry_time, errors='coerce'), pd.to_datetime(df.exit_time, errors='coerce')
def io24():
    df = pd.read_csv('한국체육산업개발주식회사_올림픽공원 입출차 정보_20240731.csv', encoding='cp949'); df.columns = ['d', 'e', 'x']
    e = pd.to_datetime(df.e, errors='coerce'); x = pd.to_datetime(df.x, errors='coerce'); return e, x, e, x
def exitinfo(E, day, st, run):
    en, ex, ea, xa = E
    B5 = lambda s: s.dropna().dt.floor('5min').value_counts()
    idx = pd.date_range(pd.Timestamp(day) + pd.Timedelta(minutes=st), periods=72, freq='5min')
    n5 = (B5(ex[(ex >= idx[0]) & (ex < idx[-1] + pd.Timedelta(minutes=5))]).reindex(idx).fillna(0) - B5(en[(en >= idx[0]) & (en < idx[-1] + pd.Timedelta(minutes=5))]).reindex(idx).fillna(0)).values
    s = n5.reshape(-1, 2).sum(1); busy = [i for i in range(6, 36) if s[i] >= 120]
    sched = run if run else 150; e0 = max(60, sched - 45)
    new = None; c = 0
    for k in range(2, 73):
        t = 5 * k; r10 = n5[k - 2] + n5[k - 1]
        if t < e0: c = 0; continue
        c = c + 1 if r10 >= 120 else 0
        if c >= 2: new = t; break
    ok = ea.notna() & xa.notna() & (xa >= ea); es = np.sort(ea[ok].values); xs = np.sort(xa[ok].values)
    g = (pd.Timestamp(day) + pd.Timedelta(minutes=st) + pd.to_timedelta(np.arange(0, 365, 5), 'm')).values
    occ = (np.searchsorted(es, g, side='right') - np.searchsorted(xs, g, side='right')).astype(float)
    old = None
    for k in range(2, len(g)):
        t = 5 * k
        if t < e0: continue
        if occ[k - 2] > 0 and (occ[k - 2] - occ[k]) / occ[k - 2] >= 0.065: old = t; break
    pk = int(6 + np.argmax(s[6:])) * 10
    return dict(alarm_new=None if new is None else st + new, alarm_old=None if old is None else st + old, bs=None if not busy else st + busy[0] * 10, pk=st + pk, be=None if not busy else st + busy[-1] * 10, pk_v=float(s[6:].max()))
OUT = {}
E25 = io25()
ev25 = []
for day in sorted(show25):
    if not day.startswith('2025'): continue
    b = [x for x in SHOW[day]['big'] if 'KSPO' in x['venue']]
    if len(b) != 1: continue
    run = b[0].get('run'); run = int(run) if run == run and run else 0
    tr = truth_day(day)
    if tr is None: continue
    st = hm(b[0]['t']); ex = exitinfo(E25, day, st, run) if day[5:7] not in ('08', '09') else None
    ev25.append(dict(d=day, st=st, run=run, name=b[0].get('short') or b[0].get('name'), truth=tr, exit=ex))
OUT['2025'] = ev25
S24 = json.load(open('../analysis/sim/sched2024.json', encoding='utf-8')); E24 = io24(); ev24 = []
for s in S24:
    tr = truth_day(s['d'])
    if tr is None: continue
    ex = exitinfo(E24, s['d'], s['st'], s['run']) if s['d'][5:7] == '07' else None
    ev24.append(dict(d=s['d'], st=s['st'], run=s['run'], name=s['name'], truth=tr, exit=ex))
OUT['2024'] = ev24
json.dump(OUT, open(os.path.expanduser('~/bt/sim_in.json'), 'w'), ensure_ascii=False)
print('2025', len(ev25), '2024', len(ev24), '2024 7월', sum(1 for e in ev24 if e['exit']))
print([ (e['d'], e['exit']) for e in ev24 if e['exit']])
