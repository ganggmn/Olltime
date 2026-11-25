"""공원 전체 사람 수를 10분 단위로 예측하는 모델 여러 개를 만들고, 서울시 실시간 '올림픽공원'(5분마다)으로 채점해요.
사용: data 폴더에서 python3 ../analysis/tenmin.py backtest   (2026-11-23~25로 채점)
      python3 ../analysis/tenmin.py freeze     (11/26~29 예측을 고정해 checks/tenmin_forecasts.json에 저장)
      python3 ../analysis/tenmin.py score 2026-11-26  (고정해 둔 예측을 그날 실제 값으로 채점)
필요: citydata/raw_*.jsonl.gz(실시간 5분), checks/park_population_2025_hourly_poi127.csv(2025년 시간별), ~/past3.pkl(날짜 종류·공연)
모델(모두 '그날 새벽 값 + 늘어나는 폭'):
  A 계단: 2025년 시간별 모양을 그 시간 내내 같은 값으로
  B 직선: 시간별 값을 매시 30분에 두고 직선으로 이음(사이트 방식에서 테두리 몫을 뺀 것)
  S 사이트: B + 테두리 오르내림 × 0.12 (월~목만, 사이트가 쓰는 식)
  C 매끈: 1시간 평균은 그대로 지키면서 10분 값을 매끈하게(평균 보존 보간)
  E 최근 실시간: 같은 종류 지난 실시간 날들의 10분 곡선(새벽 대비) 중앙값
  F 섞기: (C + E) / 2
  G 공연 시각 맞춤: 2025년 같은 요일 공연 날을 시작 시각에 맞춰 겹친 모양(공연 날만)
늘어나는 폭에 곱하는 값 s: 지난 실시간 날들에서 '실시간 증가 ÷ 2025년 증가'(그날을 빼고 배움).
2시간 앞 예측: 각 모델에 2시간 전 실제와의 차이 × 남는 비율(평일 0.94, 공연 날 0.82)을 더함(사이트와 같은 규칙)."""
import gzip, json, glob, os, sys, pickle, numpy as np, pandas as pd, datetime as dt, warnings; warnings.filterwarnings('ignore')
NB = 144; MIN10 = np.arange(NB) * 10
def load_rt():
    rows = []
    for f in sorted(glob.glob('citydata/raw_202611*.jsonl.gz')):
        for line in gzip.open(f, 'rt', encoding='utf-8'):
            try: r = json.loads(line); p = r['response']['CITYDATA']['LIVE_PPLTN_STTS'][0]
            except Exception: continue
            rows.append((pd.Timestamp(p.get('PPLTN_TIME') or r['collected_at']), float(p['AREA_PPLTN_MIN']), float(p['AREA_PPLTN_MAX'])))
    T = pd.DataFrame(rows, columns=['ts', 'lo', 'hi']).drop_duplicates('ts').sort_values('ts'); T['mid'] = (T.lo + T.hi) / 2
    T['d'] = T.ts.dt.strftime('%Y-%m-%d'); T['k'] = (T.ts.dt.hour * 60 + T.ts.dt.minute) // 10
    return T.groupby(['d', 'k']).agg(mid=('mid', 'mean'), lo=('lo', 'mean'), hi=('hi', 'mean'))
def dawn_of(RT, d):
    v = [RT.loc[(d, k), 'mid'] for k in range(12, 30) if (d, k) in RT.index]
    return float(np.median(v)) if v else None
def curve(RT, d):
    return np.array([RT.loc[(d, k), 'mid'] if (d, k) in RT.index else np.nan for k in range(NB)])
P = pickle.load(open(os.path.expanduser('~/past3.pkl'), 'rb')); G, SHOW = P['G'], P['show']
PO = pd.read_csv('checks/park_population_2025_hourly_poi127.csv'); PO['ts'] = pd.to_datetime(PO.ts); PO['d'] = PO.ts.dt.strftime('%Y-%m-%d'); PO['h'] = PO.ts.dt.hour
POI = PO.pivot_table(index='d', columns='h', values='park_pop'); POI = POI.sub(POI[[2, 3, 4]].median(axis=1), axis=0)  # 새벽 대비 증가
def clock(days): return POI.loc[[d for d in days if d in POI.index]].median().reindex(range(24)).fillna(0).values
def start_of(d, tier='big'): return min(int(s['t'][:2]) + int(s['t'][3:5]) / 60 for s in SHOW[d][tier])
def aligned(days, st_today):
    rel = {}
    for d in days:
        if d not in POI.index: continue
        st = int(start_of(d))
        for h in range(24): rel.setdefault(h - st, []).append(POI.loc[d, h])
    st = int(st_today); return np.array([np.nanmedian(rel[h - st]) if len(rel.get(h - st, [])) >= 3 else np.nan for h in range(24)])
RIM_WK = [-149, -91, -22, 0, 54, 157, 716, 467, -1993, -3681, -5037, -5174, -4879, -4989, -4474, -3340, -1350, 363, 1997, 3344, 3364, 3240, 1350, 392]  # model.js PP.wk.rim
def step(a): return np.repeat(np.asarray(a, float), 6)
def lin(a):
    a = np.asarray(a, float); x = (MIN10 + 5) / 60 - 0.5; h = np.floor(x).astype(int) % 24; f = x - np.floor(x); return a[h] + (a[(h + 1) % 24] - a[h]) * f
def mp(a, it=60):
    a = np.asarray(a, float); y = lin(a)
    for _ in range(it):
        y = y + np.repeat(a - y.reshape(24, 6).mean(1), 6)
        z = np.r_[y[0], y, y[-1]]; y = 0.25 * z[:-2] + 0.5 * z[1:-1] + 0.25 * z[2:]
    return y + np.repeat(a - y.reshape(24, 6).mean(1), 6)
def ratio(RT, days, prof):
    r = []
    for d in days:
        c = curve(RT, d) - dawn_of(RT, d); p = step(prof); m = (MIN10 >= 420) & ~np.isnan(c) & (np.abs(p) > 500)
        if m.sum() > 20: r.append(np.nansum(c[m]) / np.sum(p[m]))
    return float(np.median(r)) if r else 1.0
def models(RT, kind, train, prof, st=None, al=None, rim=False, extra_shift=0):
    s = ratio(RT, train, prof) if train else 1.0
    M = {'A 계단': s * step(prof), 'B 직선': s * lin(prof), 'C 매끈': s * mp(prof)}
    if rim: M['S 사이트'] = s * lin(prof) + 0.12 * lin(RIM_WK)
    if train:
        E = np.nanmedian(np.vstack([np.roll(curve(RT, d) - dawn_of(RT, d), extra_shift) for d in train]), axis=0)
        E = pd.Series(E).interpolate(limit_direction='both').values; M['E 최근 실시간'] = E; M['F 섞기'] = (M['C 매끈'] + E) / 2
    if al is not None:
        g = np.where(np.isnan(al), prof, al); M['G 공연 시각 맞춤'] = s * mp(g)
    return M, s
def score(RT, d, base, M, beta):
    tr = curve(RT, d); lo = np.array([RT.loc[(d, k), 'lo'] if (d, k) in RT.index else np.nan for k in range(NB)]); hi = np.array([RT.loc[(d, k), 'hi'] if (d, k) in RT.index else np.nan for k in range(NB)])
    out = {}
    for name, inc in M.items():
        p = base + inc; p2 = p.copy()
        for k in range(12, NB): p2[k] = p[k] + beta * ((tr[k - 12] if not np.isnan(tr[k - 12]) else p[k - 12]) - p[k - 12])
        m = (MIN10 >= 420) & ~np.isnan(tr); r = {}
        for lab, q in (('내일', p), ('2시간 앞', p2)):
            e = np.abs(q[m] - tr[m]); t30 = tr[m][: (m.sum() // 3) * 3].reshape(-1, 3).mean(1); q30 = q[m][: (m.sum() // 3) * 3].reshape(-1, 3).mean(1)
            r[lab] = dict(acc=round(100 * (1 - e.sum() / tr[m].sum()), 1), mae=round(float(e.mean())), inband=round(100 * float(np.mean((q[m] >= lo[m]) & (q[m] <= hi[m]))), 0), acc30=round(100 * (1 - np.abs(q30 - t30).sum() / t30.sum()), 1))
        out[name] = r
    return out
RT = load_rt()
wk25 = [d for d, g in G.items() if g == '월~목·없음']
TYPE = {'2026-11-27': ('fri', '금·큰 공연'), '2026-11-28': ('sat', '토·큰 공연'), '2026-11-29': ('sun', '일·큰 공연')}
ST = {'2026-11-27': 19.0, '2026-11-28': 18.0, '2026-11-29': 17.0}
cmd = sys.argv[1] if len(sys.argv) > 1 else 'backtest'
if cmd == 'backtest':
    days = ['2026-11-23', '2026-11-24', '2026-11-25']; prof = clock(wk25); allres = {}
    for how in ('빼고 배움', '앞선 날만'):
        print('\n== 평일 채점(%s). 07~24시, 10분 단위. 정확도 = 100×(1−Σ|오차|÷Σ실제), 범위 안 = 서울시 범위(500명 폭) 안에 든 10분 칸 비율' % how)
        for d in days:
            train = [x for x in days if x != d] if how == '빼고 배움' else [x for x in days if x < d]
            M, s = models(RT, 'wk', train, prof, rim=True); base = dawn_of(RT, d); res = score(RT, d, base, M, 0.94); allres[(how, d)] = res
            print(' %s 새벽 %.0f명, s=%.2f(배운 날 %d)' % (d, base, s, len(train)))
            for name, r in res.items(): print('   %-12s 내일 %5.1f%% (%4d명, 범위 안 %3.0f%%, 30분 %5.1f%%) | 2시간 앞 %5.1f%% (%4d명, 범위 안 %3.0f%%)' % (name, r['내일']['acc'], r['내일']['mae'], r['내일']['inband'], r['내일']['acc30'], r['2시간 앞']['acc'], r['2시간 앞']['mae'], r['2시간 앞']['inband']))
    # 공연 날 시험: 11/22(일, 오후 5시) — 2025년 일·큰 공연(시작 5시) 모양으로만(실시간 공연 날이 하루뿐이라 E는 없음)
    d = '2026-11-22'; sun = [x for x, g in G.items() if g in ('일·큰 공연',) and 'big' in SHOW.get(x, {}) and int(start_of(x)) == 17]
    prof = clock(sun); al = aligned([x for x, g in G.items() if g == '일·큰 공연' and 'big' in SHOW.get(x, {})], 17)
    v = [RT.loc[(d, k), 'mid'] for k in range(30, 42) if (d, k) in RT.index]; base = float(np.median(v)) if v else 4000
    for sname, s in (('s=1', 1.0), ('s=평일 비율 0.84', 0.84)):
        M = {'A 계단': s * step(prof), 'B 직선': s * lin(prof), 'C 매끈': s * mp(prof), 'G 공연 시각 맞춤': s * mp(np.where(np.isnan(al), prof, al))}
        res = score(RT, d, base, M, 0.82); print('\n== 공연 날 채점 %s (%s, 2025년 일요일 오후 5시 공연 %d일 모양, 새벽 대신 5~7시 %.0f명)' % (d, sname, len(sun), base))
        for name, r in res.items(): print('   %-12s 내일 %5.1f%% (%4d명, 범위 안 %3.0f%%) | 2시간 앞 %5.1f%% (%4d명, 범위 안 %3.0f%%)' % (name, r['내일']['acc'], r['내일']['mae'], r['내일']['inband'], r['2시간 앞']['acc'], r['2시간 앞']['mae'], r['2시간 앞']['inband']))
if cmd == 'freeze':
    out = {'made_at': dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec='minutes'), 'note': '각 값은 그날 새벽 값에 더할 10분별 증가(명). 내일 예측은 anchor를 더한 값. 공연 날 anchor는 최근 평일 새벽 중앙값.', 'days': {}}
    wkd = ['2026-11-23', '2026-11-24', '2026-11-25']; prof = clock(wk25)
    M, s = models(RT, 'wk', wkd, prof, rim=True); a = dawn_of(RT, '2026-11-26')
    out['days']['2026-11-26'] = dict(kind='월~목·없음', anchor=a, s=round(s, 3), beta=0.94, models={k: [round(float(x)) for x in v] for k, v in M.items()})
    rec = [dawn_of(RT, x) for x in wkd + ['2026-11-26']]; a2 = float(np.median([x for x in rec if x]))
    for d, (k, g) in TYPE.items():
        ds = [x for x, gg in G.items() if gg == g and 'big' in SHOW.get(x, {})]; prof = clock(ds); al = aligned(ds, ST[d])
        s1 = ratio(RT, wkd, clock(wk25))
        M = {'A 계단': s1 * step(prof), 'B 직선': s1 * lin(prof), 'C 매끈': s1 * mp(prof), 'G 공연 시각 맞춤': s1 * mp(np.where(np.isnan(al), prof, al)), 'G 공연 시각 맞춤 ×0.84(11/22에서 배움)': 0.84 * mp(np.where(np.isnan(al), prof, al))}
        c22 = curve(RT, '2026-11-22'); v = [RT.loc[('2026-11-22', kk), 'mid'] for kk in range(30, 42) if ('2026-11-22', kk) in RT.index]
        E = pd.Series(np.roll(c22 - np.median(v), int((ST[d] - 17) * 6))).interpolate(limit_direction='both').values
        M['E 11/22 공연 날 실시간(시각 옮김)'] = E; M['F 섞기'] = (M['G 공연 시각 맞춤'] + E) / 2
        out['days'][d] = dict(kind=g, start=ST[d], anchor=a2, s=round(s1, 3), beta=0.82, n2025=len(ds), models={kk: [round(float(x)) for x in vv] for kk, vv in M.items()})
    json.dump(out, open('checks/tenmin_forecasts.json', 'w'), ensure_ascii=False)
    for d, v in out['days'].items(): print(d, v['kind'], 'anchor', round(v['anchor']), 's', v['s'], '모델', list(v['models']), '| 18시 예측', {k: round(v['anchor'] + m[108]) for k, m in v['models'].items()})
if cmd == 'score':
    F = json.load(open(sys.argv[3] if len(sys.argv) > 3 else 'checks/tenmin_forecasts.json')); d = sys.argv[2]; v = F['days'][d]
    base_now = dawn_of(RT, d) if v['kind'].startswith('월') else v['anchor']
    M = {k: np.array(m, float) for k, m in v['models'].items()}
    for lab, base in (('고정한 새벽 값', v['anchor']), ('그날 새벽 값', dawn_of(RT, d) or v['anchor'])):
        res = score(RT, d, base, M, v['beta']); print('\n== %s %s 채점(%s %.0f명, 실시간 10분 칸 %d개)' % (d, v['kind'], lab, base, int(np.sum(~np.isnan(curve(RT, d)[42:])))))
        for name, r in sorted(res.items(), key=lambda x: -x[1]['내일']['acc']): print('   %-24s 내일 %5.1f%% (%4d명, 범위 안 %3.0f%%, 30분 %5.1f%%) | 2시간 앞 %5.1f%% (%4d명, 범위 안 %3.0f%%)' % (name, r['내일']['acc'], r['내일']['mae'], r['내일']['inband'], r['내일']['acc30'], r['2시간 앞']['acc'], r['2시간 앞']['mae'], r['2시간 앞']['inband']))
