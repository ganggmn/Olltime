"""과거 자료(2025년)로 세 구역 — 공원 안, 역→공원 통로, 테두리(750m, 동서남북) — 을 날짜 유형별로 세고,
지하철(교통카드)·버스·따릉이·주차 기록과 맞대요. 기지국(생활인구)의 성별·연령도 같이 봐요.
사용: data 폴더에서 python3 ../analysis/past3.py
필요: livingpop_zone/2025MM.csv(250_LOCAL_RESD_2025MM.zip에서 zone_cells 73칸만 뽑은 것: 총인구 + 남녀 × 14개 연령대),
      checks/zone_cells_2025.json(zone_cells.py), 서울교통공사 역별 일별 시간대별 승하차(2025), 9호선 2·3단계(2025),
      checks/shows_site_2024-12_2025-12.json, holidays.csv, inout_2025_full.csv, ../analysis/bus_park_2025.csv.gz, ../analysis/bike_park_2025.csv.gz
출력: checks/past3_2025.json(유형별 시간 프로필·구성·맞대기), checks/past3_days_2025.csv(날마다)
날짜 유형: 명절(설 1/25~30, 추석 10/3~9), 평일 공휴일, 월~목, 금, 토, 일 × 공연(큰=KSPO DOME, 중간=핸드볼경기장, 작은=올림픽홀, 야외 축제=88잔디마당, 없음).
  우리금융아트홀·뮤즈라이브는 거의 매일 있는 1천 석 안팎 공연이라 유형을 나누지 않았어요.
늘어난 만큼: 같은 요일·앞뒤 35일 안의 '공연·축제·공휴일 없는 날' 중앙값과 견줘요(zones3.py와 같은 규칙)."""
import pandas as pd, numpy as np, glob, json, math, re, os, calendar, warnings; warnings.filterwarnings('ignore')
A = '../analysis'
ZC = json.load(open('checks/zone_cells_2025.json', encoding='utf-8'))
QK = {'동': 'e', '서': 'w', '남': 's', '북': 'n', '올림픽공원': 'olp', '몽촌토성': 'mct', '한성백제': 'hsb'}
CZ = {c: ('in' if v['z'] == '공원 안' else 'dome' if v['z'] == 'DOME' else ('cor_' if v['z'] == '통로' else 'rim_') + QK[v['q']]) for c, v in ZC.items()}
ZN = {'in': '공원 안', 'dome': 'KSPO DOME 칸', 'cor_olp': '통로 올림픽공원역', 'cor_mct': '통로 몽촌토성역', 'cor_hsb': '통로 한성백제역',
      'rim_e': '테두리 동', 'rim_w': '테두리 서', 'rim_s': '테두리 남', 'rim_n': '테두리 북'}
M = ['M%02d' % i for i in range(14)]; F = ['F%02d' % i for i in range(14)]; cols = ['date', 'hour', 'dong', 'cell', 'total'] + M + F; V = ['total'] + M + F
AG = {'0~9': [0], '10대': [1, 2], '20대': [3, 4], '30대': [5, 6], '40대': [7, 8], '50대': [9, 10], '60+': [11, 12, 13]}
fr = []; star = tot = 0
for f in sorted(glob.glob('livingpop_zone/2025??.csv')):
    d = pd.read_csv(f, header=None, names=cols, dtype=str); d['cell'] = d.cell.str.strip().str[-8:]; d = d[d.cell.isin(CZ)]
    s = d[M + F].apply(lambda x: x.str.strip() == '*'); star += int(s.values.sum()); tot += s.size; fr.append(d)
D = pd.concat(fr)
for c in V: D[c] = pd.to_numeric(D[c].str.strip(), errors='coerce').fillna(0)
D['h'] = D.hour.str.strip().astype(int); D['d'] = D.date.str[:4] + '-' + D.date.str[4:6] + '-' + D.date.str[6:8]; D['z'] = D.cell.map(CZ)
Z = D.groupby(['z', 'd', 'h'])[V].sum()
ZT = Z.total.unstack('z')  # (d,h) × zone 인구
ZT['park'] = ZT['in'] + ZT['dome'] + ZT['cor_olp'];
cov = (Z[M + F].sum(axis=1) / Z.total.replace(0, np.nan)).groupby(level=0).median()
ZT['rim'] = ZT[['rim_e', 'rim_w', 'rim_s', 'rim_n']].sum(axis=1)
print('생활인구: %d일, 칸 %d개, 성별·연령 칸 중 가려진 값(*) %.1f%%, 성별·연령 합 ÷ 총인구(구역별 중앙값): %s' % (ZT.index.get_level_values(0).nunique(), D.cell.nunique(), 100 * star / tot, {k: round(float(v), 3) for k, v in cov.items()}))
# 지하철(교통카드)
a = pd.read_csv('서울교통공사_역별 일별 시간대별 승하차인원_20251231.csv', encoding='cp949', dtype=str); a = a[a['역명'].isin(['올림픽공원(한국체대)', '몽촌토성(평화의문)'])]
hc = [c for c in a.columns if c.endswith('시간대') or c in ('06시이전', '24시이후')]
A1 = a.melt(id_vars=['수송일자', '역명', '승하차구분'], value_vars=hc, var_name='hc', value_name='n')
A1['h'] = A1.hc.map(lambda c: 5 if c == '06시이전' else 24 if c == '24시이후' else int(c[:2])); A1['s'] = A1['역명'].map({'올림픽공원(한국체대)': 'olp5', '몽촌토성(평화의문)': 'mct8'})
A1['k'] = np.where(A1['승하차구분'].str.contains('승'), 'on', 'off'); A1['d'] = A1['수송일자'].str[:10]
b = pd.read_csv('9호선_서울교통공사_9호선2_3단계 역별일별시간대별승하차인원_20251231.csv', encoding='cp949', dtype=str); b = b[b['역사명'].isin(['올림픽공원', '한성백제'])]
hb = [c for c in b.columns if re.match(r'\d\d시-', c)]; B1 = b.melt(id_vars=['날짜', '역사명', '구분'], value_vars=hb, var_name='hc', value_name='n')
B1['h'] = B1.hc.str[:2].astype(int); B1['s'] = B1['역사명'].map({'올림픽공원': 'olp9', '한성백제': 'hsb9'}); B1['k'] = np.where(B1['구분'].str.contains('승'), 'on', 'off'); B1['d'] = B1['날짜'].str[:10]
X = pd.concat([A1[['d', 'h', 's', 'k', 'n']], B1[['d', 'h', 's', 'k', 'n']]]); X['n'] = pd.to_numeric(X.n.astype(str).str.replace(',', ''), errors='coerce').fillna(0)
W = X.groupby(['d', 'h', 's', 'k']).n.sum().unstack(['s', 'k']).fillna(0); W.columns = [s + '_' + k for s, k in W.columns]
for k in ('on', 'off'): W['olp_' + k] = W['olp5_' + k] + W['olp9_' + k]; W['all_' + k] = W['olp_' + k] + W['mct8_' + k] + W['hsb9_' + k]
print('지하철: %d일, 역 4곳(올림픽공원 5·9호선, 몽촌토성 8호선, 한성백제 9호선), 하루 평균 승하차 %d명' % (W.index.get_level_values(0).nunique(), W[['all_on', 'all_off']].sum().sum() / W.index.get_level_values(0).nunique()))
# 날짜 유형
S = json.load(open('checks/shows_site_2024-12_2025-12.json', encoding='utf-8'))
TIER = {'KSPO DOME': 'big', '핸드볼경기장': 'mid', '올림픽홀': 'small'}; show = {}
for s in S['list'] + S['small']:
    if not s['d'].startswith('2025'): continue
    t = 'fest' if '잔디' in s['venue'] else TIER.get(s['venue'])
    if not t or not s['t']: continue
    show.setdefault(s['d'], {}).setdefault(t, []).append(s)
hol = {r[:4] + '-' + r[4:6] + '-' + r[6:] for r in pd.read_csv('holidays.csv', dtype=str).iloc[:, 0]}
MY = {str(x.date()) for x in list(pd.date_range('2025-01-25', '2025-01-30')) + list(pd.date_range('2025-10-03', '2025-10-09'))}
days = [str(x.date()) for x in pd.date_range('2025-01-01', '2025-12-31')]
def base(d):
    wd = pd.Timestamp(d).weekday()
    return '명절' if d in MY else '평일 공휴일' if (d in hol and wd < 5) else '월~목' if wd < 4 else '금' if wd == 4 else '토' if wd == 5 else '일'
def tier(d):
    t = show.get(d, {}); return next((k for k in ('fest', 'big', 'mid', 'small') if k in t), 'none')
def start(d):
    t = tier(d); return None if t == 'none' else min(int(s['t'][:2]) + int(s['t'][3:5]) / 60 for s in show[d][t])
def name(d):
    t = tier(d); return '' if t == 'none' else show[d][t][0].get('short') or show[d][t][0].get('name', '')
TN = {'none': '없음', 'small': '작은 공연', 'mid': '중간 공연', 'big': '큰 공연', 'fest': '야외 축제'}
def grp(d):
    b, t = base(d), tier(d)
    if b == '명절': return '명절'
    if t == 'fest': return '야외 축제'
    if b == '평일 공휴일': return '평일 공휴일·' + ('없음' if t == 'none' else '공연')
    return b + '·' + TN[t]
G = {d: grp(d) for d in days}
quiet = {d for d in days if tier(d) == 'none' and d not in hol and d not in MY}
# 버스(하루), 따릉이(시간), 주차(시간)
Bs = pd.read_csv(A + '/bus_park_2025.csv.gz', dtype=str)
for c in ('on', 'off'): Bs[c] = pd.to_numeric(Bs[c], errors='coerce').fillna(0)
STOP = {'24123': (37.521024, 127.114649), '24127': (37.518515, 127.113109), '24231': (37.520913, 127.115150), '24233': (37.515528, 127.119303), '24239': (37.512883, 127.126159),
        '24240': (37.514622, 127.121810), '24241': (37.517200, 127.114631), '24244': (37.516718, 127.130899), '24246': (37.513295, 127.128597), '24247': (37.513322, 127.129330), '24396': (37.517040, 127.113603)}
pk = [(v['la'], v['lo']) for v in ZC.values() if v['z'] in ('공원 안', 'DOME') or (v['z'] == '통로' and v['q'] == '올림픽공원')]
cla, clo = np.mean([p[0] for p in pk]), np.mean([p[1] for p in pk])
def quad(la, lo):
    ang = math.degrees(math.atan2((la - cla) * 110900, (lo - clo) * 88200)); return 'e' if -45 <= ang < 45 else 'n' if 45 <= ang < 135 else 's' if -135 <= ang < -45 else 'w'
Bs['q'] = Bs.ars.map(lambda a: quad(*STOP[a]) if a in STOP else None); Bs['d'] = Bs.date.str[:4] + '-' + Bs.date.str[4:6] + '-' + Bs.date.str[6:]
BU = Bs.groupby(['d', 'q'])[['on', 'off']].sum().unstack('q').fillna(0); BU.columns = ['bus_%s_%s' % (k, q) for k, q in BU.columns]
print('버스: 정류장 %d곳(방향: %s), %d일' % (Bs.ars.nunique(), {a: quad(*STOP[a]) for a in sorted(STOP)}, BU.shape[0]))
K = pd.read_csv(A + '/bike_park_2025.csv.gz', dtype=str); K['rt'] = pd.to_datetime(K.rent_time, errors='coerce'); K['bt'] = pd.to_datetime(K.return_time, errors='coerce')
P = {'1268', '1267', '2622', '2621', '4857', '5781', '5751', '4862', '4481', '4865', '4464', '4856'}
K['rs'] = K.rent_station.str.lstrip('0'); K['bs'] = K.return_station.str.lstrip('0')
KR = K[K.rs.isin(P)]; KB = K[K.bs.isin(P)]
bike_out = KR.groupby([KR.rt.dt.strftime('%Y-%m-%d'), KR.rt.dt.hour]).size(); bike_in = KB.groupby([KB.bt.dt.strftime('%Y-%m-%d'), KB.bt.dt.hour]).size()
KR['age'] = 2025 - pd.to_numeric(KR.birth_decade, errors='coerce')
df = pd.read_csv('inout_2025_full.csv', usecols=['entry_gate', 'entry_time', 'exit_time'], encoding='utf-8-sig'); df = df[~df.entry_gate.astype(str).str.contains('CMB')]
e = pd.to_datetime(df.entry_time, errors='coerce'); x = pd.to_datetime(df.exit_time, errors='coerce'); ok = e.notna() & x.notna() & (x >= e)
es = np.sort(e[ok].values); xs = np.sort(x[ok].values); eo = e[ok]; ent = eo.groupby([eo.dt.strftime('%Y-%m-%d'), eo.dt.hour]).size()
bad_car = lambda d: d[5:7] in ('08', '09') or (d[5:7] == '11' and int(d[8:]) > 6) or (d[5:7] == '12' and int(d[8:]) > 7) or int(d[8:]) == calendar.monthrange(2025, int(d[5:7]))[1]
occ = lambda d, h: int(np.searchsorted(es, np.datetime64('%sT%02d:30' % (d, h))) - np.searchsorted(xs, np.datetime64('%sT%02d:30' % (d, h))))
# 날마다 표
rows = []
for d in days:
    if (d, 14) not in ZT.index: continue
    r = dict(d=d, wd='월화수목금토일'[pd.Timestamp(d).weekday()], grp=G[d], start=start(d), name=name(d)[:16])
    for h in (8, 13, 15, 18, 21):
        for z in ('park', 'in', 'dome', 'cor_olp', 'rim_e', 'rim_w', 'rim_s', 'rim_n'): r['%s_%d' % (z, h)] = round(ZT.loc[(d, h), z]) if (d, h) in ZT.index else None
    r['park_max'] = round(ZT.loc[d].park.max()); r['park_maxh'] = int(ZT.loc[d].park.idxmax())
    if d in W.index.get_level_values(0):
        w = W.loc[d].sum(); r.update({k: int(w[k]) for k in ('olp5_on', 'olp5_off', 'olp9_on', 'olp9_off', 'mct8_on', 'mct8_off', 'hsb9_on', 'hsb9_off')})
    if d in BU.index: r.update({k: int(v) for k, v in BU.loc[d].items()})
    r['bike_out'] = int(bike_out.loc[d].sum()) if d in bike_out.index.get_level_values(0) else 0
    r['car_in'] = None if bad_car(d) else int(ent.loc[d].sum()) if d in ent.index.get_level_values(0) else None
    r['car_occ_15'] = None if bad_car(d) else occ(d, 15); r['car_occ_20'] = None if bad_car(d) else occ(d, 20)
    rows.append(r)
R = pd.DataFrame(rows); R.to_csv('checks/past3_days_2025.csv', index=False, encoding='utf-8-sig')
ORDER = ['월~목·없음', '월~목·작은 공연', '월~목·중간 공연', '월~목·큰 공연', '금·없음', '금·작은 공연', '금·중간 공연', '금·큰 공연', '토·없음', '토·작은 공연', '토·중간 공연', '토·큰 공연',
         '일·없음', '일·작은 공연', '일·중간 공연', '일·큰 공연', '평일 공휴일·없음', '평일 공휴일·공연', '명절', '야외 축제']
ORDER = [g for g in ORDER if (R.grp == g).any()]
OUT = {'note': '2025년 서울 생활인구(250m, 시간별, 내국인) 73칸, 교통카드 승하차, 버스 정류장 하루 승하차, 따릉이 대여, 올림픽공원 주차 입출차', 'star_pct': round(100 * star / tot, 1), 'groups': {}}
# ① 유형별로 세기
print('\n== ① 날짜 유형별로 세기(중앙값). 사람 = 그 시각 그 구역에 있는 사람(기지국), 지하철·버스 = 하루 승차+하차, 따릉이 = 공원 대여소에서 빌린 수, 차 = 하루 들어온 차')
print('%-16s %3s | %6s %6s %6s %6s | %6s %6s %6s %6s | %6s %6s %6s %6s | %5s %5s %5s' % ('유형', '일', '공원8시', '13시', '18시', '21시', '테동13', '테서13', '테남13', '테북13', '올공역', '몽촌', '한성', '버스', '따릉이', '차', '차15시'))
prof = {}
for g in ORDER:
    ds = set(R.d[R.grp == g]); Q = R[R.grp == g]
    z = ZT[ZT.index.get_level_values(0).isin(ds)].groupby(level=1).median(); w = W[W.index.get_level_values(0).isin(ds)].groupby(level=1).median()
    prof[g] = dict(n=len(ds), zone={k: [round(z[k].get(h, np.nan)) for h in range(24)] for k in list(ZN) + ['park', 'rim']},
                   sub={k: [round(w[k].get(h, 0)) for h in range(5, 25)] for k in ('olp_on', 'olp_off', 'mct8_on', 'mct8_off', 'hsb9_on', 'hsb9_off')})
    tot_s = lambda p: (Q[p + '_on'] + Q[p + '_off']).median()
    bus = (Q.filter(like='bus_on').sum(axis=1) + Q.filter(like='bus_off').sum(axis=1)).median()
    print('%-16s %3d | %6.0f %6.0f %6.0f %6.0f | %6.0f %6.0f %6.0f %6.0f | %6.0f %6.0f %6.0f %6.0f | %5.0f %5s %5s' % (g, len(ds), Q.park_8.median(), Q.park_13.median(), Q.park_18.median(), Q.park_21.median(),
          Q.rim_e_13.median(), Q.rim_w_13.median(), Q.rim_s_13.median(), Q.rim_n_13.median(), (Q.olp5_on + Q.olp5_off + Q.olp9_on + Q.olp9_off).median(), tot_s('mct8'), tot_s('hsb9'), bus,
          Q.bike_out.median(), '%.0f' % Q.car_in.median() if Q.car_in.notna().any() else '-', '%.0f' % Q.car_occ_15.median() if Q.car_occ_15.notna().any() else '-'))
OUT['profiles'] = prof
# ② 성별·연령: 구역별, 시각별 구성 + 평소(월~목·없음)보다 늘어난 사람의 구성
def comp(vec):
    m = vec[M].sum(); f = vec[F].sum(); s = m + f
    if s <= 0: return None
    o = {'여성': round(100 * f / s, 1)}; o.update({k: round(100 * sum(vec[M[i]] + vec[F[i]] for i in ix) / s, 1) for k, ix in AG.items()}); return o
def gmed(zk, ds, h):
    idx = [(zk, d, h) for d in ds if (zk, d, h) in Z.index]
    return Z.loc[idx].median() if idx else None
def zsum(keys, ds, h):
    parts = [gmed(k, ds, h) for k in keys]; parts = [p for p in parts if p is not None]
    return sum(parts) if parts else None
BASE = set(R.d[R.grp == '월~목·없음'])
print('\n== ② 성별·연령(기지국). 왼쪽 = 그 시각 그 구역 전체, 오른쪽 = 평소(월~목·공연 없음, 같은 시각)보다 늘어난 사람만')
demo = {}
PARK = ['in', 'dome', 'cor_olp']; RIM = ['rim_e', 'rim_w', 'rim_s', 'rim_n']
for g in ORDER:
    ds = set(R.d[R.grp == g]); demo[g] = {}
    hs = [8, 13, 18] if g.endswith('없음') or g == '명절' else [13, 18, 20]
    for zname, keys in (('공원', PARK), ('테두리', RIM)):
        for h in hs:
            a_ = zsum(keys, ds, h); b_ = zsum(keys, BASE, h)
            if a_ is None: continue
            ca = comp(a_); ex = (a_ - b_) if b_ is not None else None
            ce = comp(ex.clip(lower=0)) if ex is not None and ex['total'] > 300 else None
            demo[g]['%s_%d' % (zname, h)] = dict(all=ca, n=round(a_['total']), ex=round(ex['total']) if ex is not None else None, excomp=ce)
    s = demo[g]
    def fmt(c): return '-' if not c else '여%4.1f 0~9 %4.1f 10대 %4.1f 20대 %4.1f 30대 %4.1f 40대 %4.1f 50대 %4.1f 60+ %4.1f' % (c['여성'], c['0~9'], c['10대'], c['20대'], c['30대'], c['40대'], c['50대'], c['60+'])
    for k, v in s.items(): print('%-16s %-9s %6d명 %s | 늘어난 %6s명 %s' % (g, k, v['n'], fmt(v['all']), v['ex'], fmt(v['excomp'])))
OUT['demo'] = demo
# 따릉이 이용자(공원 대여소에서 빌린 사람)의 성별·나이 — 기지국과 독립된 확인용
print('\n== ③ 따릉이 이용자 구성(공원 대여소에서 빌린 사람, 출생 연대·성별은 이용자가 등록한 값)')
KR['d'] = KR.rt.dt.strftime('%Y-%m-%d'); KR['g'] = KR.d.map(G); bk = {}
for g in ORDER:
    q = KR[KR.g == g]; q = q[q.sex.isin(['M', 'F'])]
    if len(q) < 100: continue
    ag = q.age; bk[g] = dict(n=len(q), 여성=round(100 * (q.sex == 'F').mean(), 1), 청소년=round(100 * (ag < 20).mean(), 1), 이십대=round(100 * ag.between(20, 29).mean(), 1), 삼사십대=round(100 * ag.between(30, 49).mean(), 1), 오십이상=round(100 * (ag >= 50).mean(), 1))
    print('%-16s %6d건 %s' % (g, len(q), bk[g]))
OUT['bike_demo'] = bk
json.dump(OUT, open('checks/past3_2025.json', 'w'), ensure_ascii=False, separators=(',', ':'))
import pickle; pickle.dump(dict(ZT=ZT, W=W, R=R, G=G, quiet=quiet, show=show, BU=BU, bike_out=bike_out, ent=ent), open(os.path.expanduser('~/past3.pkl'), 'wb'))
print('\n저장: checks/past3_2025.json, checks/past3_days_2025.csv, ~/past3.pkl')
