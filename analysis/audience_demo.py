"""공연 날 관객의 성별·나이를 2025년 서울 생활인구(250m 칸, 시간별, 성별×5세 연령대)로 어림하고,
그 구성에 따라 차로 오는 정도가 다른지 봐요.
사용: data 폴더에서 python3 ../analysis/audience_demo.py
필요: ~/grid/2025MM.csv (250_LOCAL_RESD_2025MM.zip에서 공원 16칸만 뽑은 것, grid_extract.sh),
      checks/shows_site_2024-12_2025-12.json(누리집 공연 일정), inout_2025_full.csv, holidays.csv
방법: KSPO DOME 칸(67004650)에서 공연 중(시작 1시간 뒤) 인구를, 같은 요일·같은 시각의 '큰 공연 없는 날' 중앙값과 견줘
      늘어난 만큼을 관객으로 봐요. 그 늘어난 사람의 성별·나이 비율을 그 공연의 관객 구성으로 써요."""
import os, glob, json, collections, numpy as np, pandas as pd
G = os.path.expanduser('~/grid')
cols = ['date', 'hour', 'dong', 'cell', 'total'] + ['M%02d' % i for i in range(14)] + ['F%02d' % i for i in range(14)]
AGES = ['0~9', '10~14', '15~19', '20~24', '25~29', '30~34', '35~39', '40~44', '45~49', '50~54', '55~59', '60~64', '65~69', '70+']
fr = []
for f in sorted(glob.glob(G + '/2025??.csv')):
    d = pd.read_csv(f, header=None, names=cols, dtype=str, quotechar='"')
    d['cell'] = d.cell.str.strip().str[-8:]; fr.append(d)
D = pd.concat(fr); D = D[D.cell.str.fullmatch(r'\d{8}')]
for c in cols[4:]: D[c] = pd.to_numeric(D[c].str.strip(), errors='coerce').fillna(0)
D['h'] = D.hour.str.strip().astype(int); D['d'] = D.date.str[:4] + '-' + D.date.str[4:6] + '-' + D.date.str[6:8]
DOME = D[D.cell == '67004650'].set_index(['d', 'h']).sort_index()
DOME = DOME[~DOME.index.duplicated()]
S = json.load(open('checks/shows_site_2024-12_2025-12.json', encoding='utf-8'))
dome = collections.defaultdict(list); other = collections.defaultdict(list)
for s in S['list']:
    if not s['d'].startswith('2025'): continue
    (dome if s['venue'] == 'KSPO DOME' else other)[s['d']].append(s)
hol = {r[:4] + '-' + r[4:6] + '-' + r[6:] for r in pd.read_csv('holidays.csv', dtype=str).iloc[:, 0]}
wd = lambda d: pd.Timestamp(d).weekday()
days = sorted(set(DOME.index.get_level_values(0)))
base_days = [d for d in days if d not in dome]
M = ['M%02d' % i for i in range(14)]; F = ['F%02d' % i for i in range(14)]
def base(dow, h):
    ds = [d for d in base_days if wd(d) == dow and (d, h) in DOME.index]
    return DOME.loc[[(d, h) for d in ds], ['total'] + M + F].median()
# 주차: 입출차 기록으로 그 시각 주차장 안의 차
df = pd.read_csv('inout_2025_full.csv', usecols=['entry_gate', 'entry_time', 'exit_time'], encoding='utf-8-sig')
df = df[~df.entry_gate.str.contains('CMB')]; e = pd.to_datetime(df.entry_time, errors='coerce'); x = pd.to_datetime(df.exit_time, errors='coerce')
ok = e.notna() & x.notna() & (x >= e); es = np.sort(e[ok].values); xs = np.sort(x[ok].values)
occ = lambda ts: int(np.searchsorted(es, np.datetime64(ts)) - np.searchsorted(xs, np.datetime64(ts)))
import calendar
# 입출차 원본이 빈 때: 8~9월(4대 중 1대만 남음), 11월 7일 이후, 12월 8일 이후, 매달 마지막 날
bad_month = lambda d: d[5:7] in ('08', '09') or (d[5:7] == '11' and int(d[8:]) > 6) or (d[5:7] == '12' and int(d[8:]) > 7) or int(d[8:]) == calendar.monthrange(int(d[:4]), int(d[5:7]))[1]
def carbase(dow, h):
    ds = [d for d in base_days if wd(d) == dow and not bad_month(d) and d not in hol]
    return np.median([occ(pd.Timestamp(d) + pd.Timedelta(hours=h, minutes=30)) for d in ds])
rows = []
for d, L in sorted(dome.items()):
    if (d, 0) not in DOME.index: continue
    t0 = min(int(s['t'][:2]) for s in L); h = t0 + 1
    if (d, h) not in DOME.index: continue
    b = base(wd(d), h); a = DOME.loc[(d, h), ['total'] + M + F]
    ex = (a - b).clip(lower=0); tot = ex['total']
    if tot < 1000: continue
    m = ex[M].sum(); f = ex[F].sum(); s_ = m + f
    age = {k: (ex[M[i]] + ex[F[i]]) / s_ for i, k in enumerate(AGES)}
    row = dict(d=d, wd='월화수목금토일'[wd(d)], hol=d in hol, start=L[0]['t'], name=L[0]['short'][:14], excess=round(tot), female=round(100 * f / s_, 1),
               a10=round(100 * (age['10~14'] + age['15~19']), 1), a20=round(100 * (age['20~24'] + age['25~29']), 1), a30=round(100 * (age['30~34'] + age['35~39']), 1),
               a40=round(100 * (age['40~44'] + age['45~49']), 1), a50=round(100 * (age['50~54'] + age['55~59']), 1), a60=round(100 * (age['60~64'] + age['65~69'] + age['70+']), 1),
               others=len(other.get(d, [])))
    if not bad_month(d):
        c = occ(pd.Timestamp(d) + pd.Timedelta(hours=h, minutes=30)); cb = carbase(wd(d), h)
        row.update(cars=c, car_excess=round(c - cb), cars_per_1000=round(1000 * (c - cb) / tot, 1))
    rows.append(row)
R = pd.DataFrame(rows)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
print(R.to_string(index=False))
R.to_csv('checks/audience_demo_2025.csv', index=False, encoding='utf-8-sig')
Q = R.dropna(subset=['cars_per_1000'])
R2 = R.dropna(subset=['car_excess']).copy()
R2['grp'] = np.select([R2.a50 + R2.a60 >= 60, R2.a30 + R2.a40 >= 60, R2.a10 + R2.a20 >= 60], ['50대 이상 중심', '30~40대 중심', '10~20대 중심'], '섞임')
R2['day'] = np.where(R2.wd == '금', '금', np.where(R2.wd.isin(['토', '일']), '토·일', '그 밖'))
print('\n관객 나이대별, 공연 시작 1시간 뒤 주차장 차가 평소(같은 요일·시각, KSPO DOME 공연 없는 날 중앙값)보다 늘어난 대수')
print(R2.groupby(['day', 'grp']).agg(날=('d', 'size'), 늘어난_차_중앙값=('car_excess', 'median'), 여성_중앙값=('female', 'median')).round(0).to_string())
Q = Q[Q.others == 0]  # 다른 공연장 공연이 겹치지 않은 날만
print('\n차 비교에 쓴 날(다른 공연장과 겹치지 않음, 주차 기록이 온전한 달):', len(Q))
for c in ['female', 'a20', 'a30', 'a40', 'a50', 'a60']:
    print('  관객 1,000명당 늘어난 차 vs %-6s 상관 %+.2f' % (c, np.corrcoef(Q[c], Q.cars_per_1000)[0, 1]))
Q = Q.assign(old=Q.a40 + Q.a50 + Q.a60)
for lab, mk in (('40대 이상이 절반 넘음', Q.old >= 50), ('40대 이상이 절반 안 됨', Q.old < 50)):
    print('  %-14s %2d일  1,000명당 차 중앙값 %.0f대  여성 비율 중앙값 %.0f%%' % (lab, mk.sum(), Q[mk].cars_per_1000.median(), Q[mk].female.median()))
