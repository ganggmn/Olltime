"""공연 종료 감지기: 실시간 주차 대수가 빠르게 줄기 시작하면 '공연이 끝났다'고 봐요(주차는 시각만 쓰고, 사람 수로 바꾸지 않아요).
사용: data 폴더에서 python3 ../analysis/end_detect.py   → checks/end_detect_2025.json
1) 2025년 입출차 기록(차 한 대씩 들어오고 나간 시각)으로 KSPO DOME 공연 저녁마다 5분 주차 대수와 5분 출차 수를 만들어요.
2) 정답(사후): 그날 저녁 전체 출차 곡선에서 '출차가 몰리기 시작한 시각'. 시작 60분 뒤~330분 사이 15분 평균 출차가 가장 많은 칸에서
   거꾸로 걸어가, 공연 중 수준 + (가장 많을 때 − 공연 중 수준) × 0.3 아래로 내려가기 직전 칸.
3) 예정 종료: 시작 + 공지된 공연 길이(모르면 150분). 하루 전에 아는 값.
4) 감지(실시간): 시작 60분 뒤부터 5분마다, 10분 전보다 주차 대수가 θ대 이상 줄었으면 그때 종료로 봐요. 그 시각까지의 값만 씀.
   θ는 1~6월 저녁으로 정하고(오경보 5% 이하에서 감지가 가장 빠른 값), 7·10·11월 저녁으로 채점해요.
8~9월은 원본이 4대 중 1대만 남아 있고 12월은 입차 원본이 없어 뺐어요."""
import os, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
S = json.load(open('checks/shows_site_2024-12_2025-12.json', encoding='utf-8'))['list']
DOME = {}
for x in S:
    if x['venue'] == 'KSPO DOME' and x['d'].startswith('2025'):
        DOME.setdefault(x['d'], []).append(x)
MONTHS_OK = {1, 2, 3, 4, 5, 6, 7, 10, 11}
days = sorted(d for d in DOME if int(d[5:7]) in MONTHS_OK and len(DOME[d]) == 1)
IO = pd.read_csv('inout_2025_full.csv', usecols=['entry_time', 'exit_time'])
e = pd.to_datetime(IO.entry_time, errors='coerce'); x = pd.to_datetime(IO.exit_time, errors='coerce'); ok = e.notna() & x.notna() & (x >= e); e, x = e[ok].values, x[ok].values
xs = np.sort(x); es = np.sort(e)
def evening_fast(d):
    t0 = pd.Timestamp(d + ' 12:00'); grid = pd.date_range(t0, periods=12 * 14, freq='5min'); g = grid.values
    occ = np.searchsorted(es, g, side='right') - np.searchsorted(xs, g, side='right')
    ex = np.diff(np.searchsorted(xs, np.r_[g, g[-1] + np.timedelta64(5, 'm')], side='left'))
    return grid, occ.astype(float), ex.astype(float)
REC = []
for d in days:
    s = DOME[d][0]; st = pd.Timestamp(d + ' ' + s['t']); run = s.get('run')
    grid, occ, ex = evening_fast(d)
    mins = ((grid - st) / pd.Timedelta(minutes=1)).values
    sm = pd.Series(ex).rolling(3, center=True, min_periods=1).mean().values
    show = (mins >= 30) & (mins <= 90); after = (mins >= 60) & (mins <= 330)
    if after.sum() < 10 or ex[after].sum() < 100: continue
    base = np.median(sm[show]); ia = np.where(after)[0]; ip = ia[np.argmax(sm[ia])]; peak = sm[ip]; thr = base + 0.3 * (peak - base)
    i = ip
    while i - 1 >= ia[0] and sm[i - 1] >= thr: i -= 1   # 가장 많이 나간 때에서 거꾸로 걸어가 몰리기 시작한 칸
    onset = mins[i]
    REC.append(dict(d=d, name=s.get('short') or s.get('name'), start=s['t'], run=run, sched=(run if run else 150), onset=onset, peak5=float(ex[after].max()),
                    mins=mins.tolist(), occ=occ.tolist(), wd=pd.Timestamp(d).weekday()))
print('KSPO DOME 저녁 %d일(하루 한 번 공연, 1~7·10·11월)' % len(REC))
RULE = {'kind': 'drop10'}
def detect(r, theta, earliest=None):
    m = np.array(r['mins']); o = np.array(r['occ']); k = RULE['kind']
    e0 = (r['sched'] - 45) if earliest is None else earliest
    e0 = max(e0, 60)
    for i in range(2, len(m)):
        if m[i] < e0: continue
        if k == 'drop10' and o[i - 2] - o[i] >= theta: return float(m[i])
        if k == 'two5' and o[i - 2] - o[i - 1] >= theta and o[i - 1] - o[i] >= theta: return float(m[i])
        if k == 'rel10' and o[i - 2] - o[i] >= theta / 1000 * max(o[i - 2], 1): return float(m[i])
    return None
def evaluate(R, theta):
    out = []
    for r in R:
        f = detect(r, theta); out.append(dict(d=r['d'], onset=r['onset'], fire=f, delay=None if f is None else f - r['onset'], sched_err=r['sched'] - r['onset']))
    return out
def summary(E):
    dl = np.array([z['delay'] for z in E if z['delay'] is not None]); miss = sum(1 for z in E if z['delay'] is None)
    early = int(np.sum(dl < -20)); se = np.array([z['sched_err'] for z in E])
    return dict(n=len(E), miss=miss, false_early=early, delay_med=float(np.median(dl)) if len(dl) else None, delay_p10=float(np.percentile(dl, 10)) if len(dl) else None,
                delay_p90=float(np.percentile(dl, 90)) if len(dl) else None, abs_delay_med=float(np.median(np.abs(dl))) if len(dl) else None,
                sched_abs_err_med=float(np.median(np.abs(se))), sched_err_p10=float(np.percentile(se, 10)), sched_err_p90=float(np.percentile(se, 90)))
TR = [r for r in REC if int(r['d'][5:7]) <= 6]; TE = [r for r in REC if int(r['d'][5:7]) >= 7]
cands = []
for kind, ths in (('drop10', range(20, 200, 5)), ('two5', range(10, 100, 5)), ('rel10', range(10, 120, 5))):
    RULE['kind'] = kind
    for th in ths:
        s_ = summary(evaluate(TR, th)); fe = (s_['false_early'] + s_['miss']) / s_['n']
        cands.append((kind, th, fe, s_['abs_delay_med'] if s_['abs_delay_med'] is not None else 1e9, s_['delay_p90'] if s_['delay_p90'] is not None else 1e9))
ok_ = [c for c in cands if c[2] <= 0.05]
best = min(ok_, key=lambda c: (c[3], c[4])) if ok_ else ('drop10', 60, 1, 1e9, 1e9)
RULE['kind'], theta = best[0], best[1]
for kind in ('drop10', 'two5', 'rel10'):
    b = [c for c in ok_ if c[0] == kind]
    if b: b = min(b, key=lambda c: (c[3], c[4])); print('  후보 %-6s θ=%3d: 1~6월 놓침·이른 울림 %.0f%%, |감지 지연| 중앙 %.0f분, 90%% %.0f분' % (b[0], b[1], 100 * b[2], b[3], b[4]))
print('고른 규칙(1~6월로 정함): %s, θ=%d (drop10=10분 동안 줄어든 대수, two5=5분씩 두 번 연속 줄어든 대수, rel10=10분 동안 줄어든 비율 ‰). 예정 종료 45분 전부터 봄' % (RULE['kind'], theta))
out = {'rule': RULE['kind'], 'theta': theta, 'earliest': 'max(시작+60분, 예정 종료−45분)'}
for lab, R in (('1~6월(정할 때 쓴 저녁)', TR), ('7·10·11월(채점)', TE)):
    E = evaluate(R, theta); s_ = summary(E); out[lab] = dict(summary=s_, evenings=E)
    print('[%s] %d저녁 | 감지 못 함 %d | 20분 넘게 이르게 울림 %d | 감지 − 실제 출차 시작: 중앙 %+.0f분 (10~90%%: %+.0f ~ %+.0f), 절댓값 중앙 %.0f분 | 예정 종료 − 실제: 절댓값 중앙 %.0f분 (10~90%%: %+.0f ~ %+.0f)' % (
        lab, s_['n'], s_['miss'], s_['false_early'], s_['delay_med'], s_['delay_p10'], s_['delay_p90'], s_['abs_delay_med'], s_['sched_abs_err_med'], s_['sched_err_p10'], s_['sched_err_p90']))
print('실제 출차 시작(시작 뒤 분): 중앙 %.0f분, 10~90%% %.0f ~ %.0f분, 공연 길이를 아는 저녁 %d일' % (np.median([r['onset'] for r in REC]), np.percentile([r['onset'] for r in REC], 10), np.percentile([r['onset'] for r in REC], 90), sum(1 for r in REC if r['run'])))
json.dump(out, open('checks/end_detect_2025.json', 'w'), ensure_ascii=False, indent=1)
