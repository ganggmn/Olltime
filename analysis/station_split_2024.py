"""2024년 새 자료로 '역 승차 시험'을 다시 해요(2025에서 정한 방법을 그대로 고정, 2026-11-27).
고정한 것(모두 2025 자료에서만): 퇴장 시작 확률 P0(2025 저녁 71개), 출차 모양(2025 중앙값)을 사람용으로 0.5배 압축, 걷는 시간 0분,
  점 예측(시작 시각별 2025 중앙값 / 적힌 공연 시간+42분), 과거 평균 몫(2025, 같은 시작 시각, 9호선 두 역만), 기준·지표.
2024 정답: 9호선 올림픽공원·한성백제 1시간 승차 − 같은 요일·큰 공연장(KSPO DOME, 핸드볼경기장) 공연 없는 2024 날 중 가까운 6일 중앙값(120일 안, 3일 이상).
  시작 다음 시간 ~ 24시대(9호선 00~01시는 전날 24시대). 늘어난 승차 합이 350명 이상인 저녁만. 1~8호선 2024 파일이 없어서 9호선만 봐요(2025에서 늘어난 승차의 약 71%).
2024 공연: KOPIS 일별(KSPO DOME 공연 있는 날) × KOPIS 공연 정보의 요일별 시각. 그날 시각이 하나뿐인 단독 공연만.
주 비교: 확률표(P0) vs 과거 평균 몫 — TV, 시간대 몫 제곱오차, 가장 혼잡한 시간 Brier. 보조: 확률표 vs 점 두 개, 음성 대조(2025 다른 저녁의 실제 끝을 빌림).
투어(공연명) 묶음 재표집 4000번. 사용: data 폴더에서 python3 ../analysis/station_split_2024.py schedule | score"""
import os, sys, re, csv, json, numpy as np, pandas as pd
from collections import defaultdict
MODE = sys.argv[1] if len(sys.argv) > 1 else 'schedule'
__file__ = os.path.abspath(__file__); HERE = os.path.dirname(__file__)
src = open(os.path.join(HERE, 'station_split_backtest.py'), encoding='utf-8').read()
exec(src.split("WS = [(w, c)")[0].replace("HERE = os.path.dirname(os.path.abspath(__file__)); ", ""))  # 2025 ACT, E, EVN, 함수들
W_FIX, C_FIX, MIN_EXTRA = 0, 0.5, 350
S9 = [s for s in STATIONS if '(9)' in s]
HOL24 = {'2024-01-01', '2024-02-09', '2024-02-10', '2024-02-11', '2024-02-12', '2024-03-01', '2024-04-10', '2024-05-05', '2024-05-06', '2024-05-15', '2024-06-06',
         '2024-08-15', '2024-09-16', '2024-09-17', '2024-09-18', '2024-10-01', '2024-10-03', '2024-10-09', '2024-12-25'}
# ---- 2024 9호선 승차
ON9 = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
for fn in ['9호선_서울교통공사_9호선2_3단계 역별일별시간대별승하차인원_20241231.csv', '9호선_서울교통공사_9호선2_3단계 역별일별시간대별승하차인원_20251231.csv']:
    rd = csv.reader(open_any(fn)); head = next(rd); col = {n.strip(): i for i, n in enumerate(head)}
    i_d = next(i for n, i in col.items() if '날짜' in n or '일자' in n); i_n = next(i for n, i in col.items() if '역사명' in n or '역명' in n); i_k = next(i for n, i in col.items() if '구분' in n)
    hrs = [(i, int(re.match(r'(\d{2})', n.strip()).group(1))) for n, i in col.items() if re.match(r'\d{2}시', n.strip())]
    for row in rd:
        nm = row[i_n]
        if not any(s in nm for s in ('올림픽공원', '한성백제')) or '승차' not in row[i_k]: continue
        d = pd.Timestamp(row[i_d][:10]); key = ('올림픽공원' if '올림픽공원' in nm else '한성백제') + '(9)'
        for i, h in hrs:
            v = float(row[i].replace(',', '') or 0)
            if h == 0: ON9[key][str((d - pd.Timedelta(days=1)).date())][24] += v
            else: ON9[key][str(d.date())][h] += v
# ---- 2024 공연 일정
daily = pd.concat([pd.read_csv(os.path.join(HERE, f)) for f in ['kopis_daily_20240101_20240531.csv', 'kopis_daily_20240601_20241031.csv', 'kopis_daily_20241101_20241231.csv']])
daily['d'] = pd.to_datetime(daily['from'].astype(str)).dt.strftime('%Y-%m-%d')
dome_days = sorted(daily[daily.prfnmplc.str.contains('KSPO') & (daily.prfcnt > 0)].d)
big_days = set(daily[(daily.prfnmplc.str.contains('KSPO') | daily.prfnmplc.str.contains('핸드볼')) & (daily.prfcnt > 0)].d)
meta = pd.read_csv(os.path.join(HERE, 'kopis_meta_2024_2025.csv')); meta = meta[meta.fcltynm.str.contains('KSPO', na=False)]
WD = '월화수목금토일'
def parse_dt(s):
    out = {}
    for d1, d2, t in re.findall(r'([월화수목금토일])요일(?:\s*~\s*([월화수목금토일])요일)?\(([^)]*)\)', str(s)):
        a = WD.index(d1); b = WD.index(d2) if d2 else a
        for w in range(a, b + 1): out[w] = [x.strip() for x in t.split(',') if x.strip()]
    return out
def runmin(s):
    m = re.match(r'(?:(\d+)시간)?\s*(?:(\d+)분)?', str(s)); return (int(m.group(1) or 0) * 60 + int(m.group(2) or 0)) or None if m and (m.group(1) or m.group(2)) else None
sched, why = [], defaultdict(int)
for d in dome_days:
    if not d.startswith('2024'): continue
    cov = meta[(meta.prfpdfrom.str.replace('.', '-') <= d) & (meta.prfpdto.str.replace('.', '-') >= d)]
    if len(cov) != 1: why['공연 정보 %d건' % len(cov)] += 1; continue
    r = cov.iloc[0]; times = parse_dt(r.dtguidance).get(pd.Timestamp(d).weekday())
    if not times: why['그 요일 시각 없음'] += 1; continue
    if len(times) != 1: why['하루 두 번'] += 1; continue
    sched.append(dict(d=d, t=times[0], st=hm(times[0]), run=runmin(r.prfruntime), seq=r.prfnm))
S = pd.DataFrame(sched)
NOS = {w: [x for x in sorted(ON9[S9[0]]) if x.startswith('2024') and pd.Timestamp(x).weekday() == w and x not in big_days and x not in HOL24] for w in range(7)}
def base9(s, d, h):
    t = pd.Timestamp(d); c = sorted((abs((pd.Timestamp(x) - t).days), x) for x in NOS[t.weekday()]); near = [x for k, x in c if k <= 120][:6]
    return float(np.median([ON9[s][x].get(h, 0) for x in near])) if len(near) >= 3 else np.nan
ACT24 = {}
for r in S.itertuples():
    h0 = int(r.st) // 60 + 1; H = [h for h in HRS if h >= h0]
    tot = sum(np.array([ON9[s][r.d].get(h, 0) - base9(s, r.d, h) for h in H]) for s in S9)
    if np.isnan(tot).any(): why['바닥 없음'] += 1; continue
    ACT24[r.d] = (H, tot)
print('2024 KSPO DOME 공연 날 %d일 → 단독 시각 %d저녁(뺀 이유: %s), 바닥 있는 저녁 %d(공연 %d개)' % (sum(d.startswith('2024') for d in dome_days), len(S), dict(why), len(ACT24), S[S.d.isin(ACT24)].seq.nunique()))
print('공연 없는 날(요일별, 2024): ' + ', '.join('%s %d' % (WD[w], len(v)) for w, v in NOS.items()))
print('시작 시각: ' + ', '.join('%s %d' % (k, v) for k, v in S[S.d.isin(ACT24)].t.value_counts().sort_index().items()))
if MODE == 'schedule': sys.exit(0)
# ---------------- 채점 (고정한 방법) ----------------
keep = [d for d in ACT24 if np.clip(ACT24[d][1], 0, None).sum() >= MIN_EXTRA]
T = S[S.d.isin(keep)].reset_index(drop=True)
print('늘어난 승차 %d명 이상 저녁: %d개(공연 %d개), 늘어난 승차 중앙값 %.0f명' % (MIN_EXTRA, len(T), T.seq.nunique(), np.median([np.clip(ACT24[d][1], 0, None).sum() for d in keep])))
shape = np.median(np.vstack(EVN['shape'].values), axis=0); shape /= shape.sum(); shape = squeeze(shape, C_FIX)
act25_9 = {d: (ACT[d][0], sum(ACT[d][2][s] for s in S9)) for d in E.d}  # 2025 과거 평균은 9호선 두 역만
rows = []
for r in T.itertuples():
    H, tot = ACT24[r.d]; a = share(tot); pk = int(np.argmax(a)); sh = int(r.st) // 60
    same = EVN[(EVN.st // 60) == sh]; med = float(np.median((same if len(same) >= 5 else EVN).onset))
    sm = [q for q in E.itertuples() if int(q.st) // 60 == sh]
    if len(sm) < 3: sm = list(E.itertuples())
    avg = np.zeros(len(H)); pkc = np.zeros(len(H))
    for q in sm:
        Hq, tq = act25_9[q.d]; sq = dict(zip(Hq, share(tq))); vq = np.array([sq.get(h - sh + int(q.st) // 60, 0) for h in H]); avg += vq; pkc[int(np.argmax(vq))] += 1
    def peakprob(p5):
        v = np.zeros(len(H))
        for g, pg in zip(G5, p5):
            if pg > 1e-4: v[int(np.argmax(pred_share(kde([g], bw=0.1), r.st, shape, W_FIX, H)))] += pg
        return v / v.sum()
    oth = EVN[(EVN.st // 60) == sh]; oth = oth if len(oth) else EVN
    p0 = onset_dist(EVN, r.st, r.run, 'P0')
    F = {'확률표(P0)': (pred_share(p0, r.st, shape, W_FIX, H), peakprob(p0)),
         '과거 평균 몫(2025)': (avg / avg.sum(), pkc / pkc.sum()),
         '점: 시작 시각별 중앙값': None, '점: 적힌 시간+42분': None,
         '음성 대조(2025 다른 저녁의 끝)': None}
    for k, s0 in (('점: 시작 시각별 중앙값', med), ('점: 적힌 시간+42분', (r.run or 150) + 42), ('음성 대조(2025 다른 저녁의 끝)', float(oth.onset.iloc[int(r.d.replace('-', '')) % len(oth)]))):
        v = pred_share(kde([s0], bw=0.1), r.st, shape, W_FIX, H); F[k] = (v, np.eye(len(H))[int(np.argmax(v))])
    for k, (v, pp) in F.items():
        rows.append(dict(d=r.d, seq=r.seq, t=r.t, how=k, tv=tv(v, a), se=float(((v - a) ** 2).sum()), br=float(((pp - np.eye(len(H))[pk]) ** 2).sum()), hit=int(np.argmax(v) == pk)))
R = pd.DataFrame(rows)
def boot(a, b, g, n=4000):
    us = np.unique(g); rng = np.random.default_rng(1); idx = {u: np.where(g == u)[0] for u in us}; out = []
    for _ in range(n):
        m = np.concatenate([idx[u] for u in rng.choice(us, len(us))]); out.append(a[m].mean() - b[m].mean())
    out = np.array(out); return np.percentile(out, [2.5, 97.5]), np.percentile(out, [0.5, 99.5]), 2 * min((out >= 0).mean(), (out <= 0).mean())
print('\n== 2024 결과(9호선 올림픽공원·한성백제, %d저녁) — 낮을수록 좋음' % R.d.nunique())
for k in F:
    x = R[R.how == k]; print('  %-28s TV %.3f | 제곱오차 %.3f | 최고시간 Brier %.3f | 최고시간 맞힘 %3.0f%%' % (k, x.tv.mean(), x.se.mean(), x.br.mean(), 100 * x.hit.mean()))
A = R[R.how == '확률표(P0)'].reset_index(drop=True); out = {}
for k in ('과거 평균 몫(2025)', '점: 시작 시각별 중앙값', '점: 적힌 시간+42분', '음성 대조(2025 다른 저녁의 끝)'):
    B = R[R.how == k].reset_index(drop=True); tag = '주 비교' if k == '과거 평균 몫(2025)' else '보조'
    for m, lab in (('tv', 'TV'), ('se', '제곱오차'), ('br', '최고시간 Brier')):
        ci, ci99, p = boot(A[m].values, B[m].values, A.seq.values); out['%s|%s' % (k, m)] = dict(diff=float(A[m].mean() - B[m].mean()), ci95=list(ci), ci99=list(ci99), p=float(p))
        print('  [%s] 확률표 − %-26s %-12s %+.3f (95%% %+.3f ~ %+.3f, 99%% %+.3f ~ %+.3f, p=%.3f)' % (tag, k, lab, A[m].mean() - B[m].mean(), *ci, *ci99, p))
B = R[R.how == '음성 대조(2025 다른 저녁의 끝)'].reset_index(drop=True); C_ = R[R.how == '과거 평균 몫(2025)'].reset_index(drop=True)
ci, _, p = boot(B.tv.values, C_.tv.values, B.seq.values); print('  [시험의 힘] 음성 대조 − 과거 평균 TV %+.3f (95%% %+.3f ~ %+.3f, p=%.3f)' % (B.tv.mean() - C_.tv.mean(), *ci, p))
for sth in sorted(T.st.astype(int) // 60):
    pass
for sth in sorted(set(T.st.astype(int) // 60)):
    x = [ACT24[d] for d in T[T.st.astype(int) // 60 == sth].d]; Hs = list(range(sth + 1, 25))
    m = np.mean([[dict(zip(H, share(t))).get(h, 0) for h in Hs] for H, t in x], axis=0)
    print('  2024 %d시 시작 %d저녁 실제 평균 몫: ' % (sth, len(x)) + ', '.join('%d시대 %.0f%%' % (h, 100 * v) for h, v in zip(Hs, m) if v >= 0.005))
R.to_csv('checks/station_split_2024.csv', index=False); json.dump(out, open('checks/station_split_2024.json', 'w'), ensure_ascii=False, indent=1)
