"""'시각 + 걷기' 예측을 역 승차로 시험(2025 KSPO DOME 저녁, 미래를 모른다고 놓고).
예측: 퇴장 시작 확률(exitprob P0, 그 투어를 뺀 나머지로) × 나가는 모양(주차 출차 시작 뒤 2시간 모양, 시각에만 씀) → 걷는 시간 W만큼 미룸 → 1시간 칸으로 묶어
      '공연 뒤 늘어난 승차가 시간대별로 어떻게 나뉠지'(몫)를 맞힘. W는 다른 투어 저녁들(실제 출차 시작)로 고름.
정답: 올림픽공원역(5·9호선)·몽촌토성역(8호선)·한성백제역(9호선) 1시간 승차 − 같은 요일 공연 없는 날(±6주) 중앙값. 시작 다음 시간 ~ 24시대.
비교: 점 예측(시작 시각별 중앙값, 예정+42분), 과거 평균 몫(같은 시작 시각대 다른 투어), 정답 시작을 안다면.
지표: 시간대 몫 차이 TV = ½Σ|예측 몫 − 실제 몫|(0이면 완벽), 가장 붐빈 시간 맞힘, 그 시간에 준 몫. 투어 묶음 재표집.
사람 수는 판매수 없이 몫만 봐요(주차 대수로 사람 수를 만들지 않음). 10분 모양은 1시간 자료로 확인할 수 없어요.
사용: data 폴더에서 python3 ../analysis/station_split_backtest.py"""
import os, sys, re, csv, json, numpy as np, pandas as pd
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); sys.argv = [sys.argv[0], 'none']
exec(open(os.path.join(HERE, 'exitprob.py'), encoding='utf-8').read().split("if __name__ == '__main__' and sys.argv[1] == 'backtest':")[0])
STN = ('올림픽공원', '몽촌토성', '한성백제')
def open_any(p):
    for e in ('utf-8-sig', 'cp949'):
        try: f = open(p, encoding=e, newline=''); f.read(4096); f.seek(0); return f
        except UnicodeDecodeError: pass
ON = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))  # ON[역][날짜][시] (24 = 24~25시)
for fn in ['서울교통공사_역별 일별 시간대별 승하차인원_20251231.csv', '9호선_서울교통공사_9호선2_3단계 역별일별시간대별승하차인원_20251231.csv', '9호선_서울교통공사_9호선2_3단계 역별일별시간대별승하차인원_20260731.csv']:
    if not os.path.exists(fn): continue
    rd = csv.reader(open_any(fn)); head = next(rd); col = {n.strip(): i for i, n in enumerate(head)}
    i_d = next(i for n, i in col.items() if '일자' in n or '날짜' in n); i_n = next(i for n, i in col.items() if '역명' in n or '역사명' in n)
    i_k = next(i for n, i in col.items() if '구분' in n); i_l = col.get('호선')
    hrs = []
    for n, i in col.items():
        m = re.match(r'(\d{2})', n.strip())
        if not m or '시' not in n: continue
        h = int(m.group(1)); h = h - 1 if '이전' in n else h; hrs.append((i, h))
    nine = '9호선' in fn
    for row in rd:
        nm = row[i_n]
        if not any(s in nm for s in STN) or '승차' not in row[i_k]: continue
        d = pd.Timestamp(row[i_d][:10]); key = next(s for s in STN if s in nm) + '(' + row[i_l].replace('호선', '') + ')'
        for i, h in hrs:
            try: v = float(row[i].replace(',', '') or 0)
            except ValueError: continue
            if nine and h == 0: ON[key][str((d - pd.Timedelta(days=1)).date())][24] += v  # 9호선 00~01시는 전날 24시대로
            else: ON[key][str(d.date())][h] += v
STATIONS = sorted(ON)
days_all = sorted(set().union(*[set(ON[s]) for s in STATIONS]))
# 바닥: 같은 요일, 큰 공연장(KSPO DOME 등) 공연이 없는 2025 날. 토·일은 작은 공연장 공연이 없는 날이 없어서 작은 공연은 허용해요(바닥이 조금 높게 잡힘).
NOSHOW = {w: [x for x in days_all if x[:4] == '2025' and pd.Timestamp(x).weekday() == w and not SHOW.get(x, {}).get('big') and x not in HOL and x in ON[STATIONS[0]]] for w in range(7)}
def base(s, d, h):
    # 같은 요일, 공원 공연이 하나도 없는 2025 날 중 날짜가 가까운 6일(120일 안), 3일 넘게 있어야 씀
    t = pd.Timestamp(d); c = sorted((abs((pd.Timestamp(x) - t).days), x) for x in NOSHOW[t.weekday()])
    near = [x for k, x in c if k <= 120][:6]
    return float(np.median([ON[s][x].get(h, 0) for x in near])) if len(near) >= 3 else np.nan
HRS = list(range(14, 25))
def actual(r):
    h0 = int(r.st) // 60 + 1; H = [h for h in HRS if h >= h0]
    ext = {s: np.array([ON[s][r.d].get(h, 0) - base(s, r.d, h) for h in H]) for s in STATIONS}
    tot = sum(ext.values()); return H, tot, ext
def squeeze(shape, c):
    if c == 1: return shape
    x = np.arange(len(shape)) * 5.0; xs = np.arange(0, len(shape) * 5.0, 5.0)
    v = np.interp(xs / c, x, shape, right=0); return v / v.sum()
def pred_share(p5, st, shape, W, H):
    flow = np.zeros(2200); st = int(st) + 120
    for g, pg in zip(G5, p5):
        if pg <= 0: continue
        for j, sj in enumerate(shape): flow[st + int(g) + 5 * j + W: st + int(g) + 5 * j + W + 5] += pg * sj / 5
    v = np.array([flow[60 * h + 120: 60 * h + 180].sum() for h in H]); return v / v.sum() if v.sum() > 0 else v
def share(v): v = np.clip(v, 0, None); return v / v.sum() if v.sum() > 0 else v
tv = lambda a, b: 0.5 * np.abs(a - b).sum()
small_same = lambda d: any(x['venue'] != 'KSPO DOME' and hm(x['t']) >= 15 * 60 for x in SHOW.get(d, {}).get('small', []) + SHOW.get(d, {}).get('big', []))
ACT = {}
for r in EVN.itertuples():
    if r.d not in days_all: continue
    H, tot, ext = actual(r)
    if np.isnan(tot).any() or np.clip(tot, 0, None).sum() < 500: continue
    ACT[r.d] = (H, tot, ext)
E = EVN[EVN.d.isin(ACT)].reset_index(drop=True)
print('공연 없는 날(요일별): ' + ', '.join('%s %d' % ('월화수목금토일'[w], len(v)) for w, v in NOSHOW.items()))
print('역: %s | 2025 저녁 %d개(투어 %d개), 그중 같은 저녁 다른 공연장 공연 없음 %d개' % (', '.join(STATIONS), len(E), E.seq.nunique(), sum(not small_same(d) for d in E.d)))
print('공연 뒤 늘어난 승차(시작 다음 시간~24시대, 네 역 합): 중앙값 %.0f명' % np.median([np.clip(ACT[d][1], 0, None).sum() for d in E.d]))
WS = [(w, c) for w in range(-30, 35, 5) for c in (1.0, 0.5, 0.25)]; rows = []
for r in E.itertuples():
    tr = E[E.seq != r.seq]; trv = EVN[EVN.seq != r.seq]
    shape = np.median(np.vstack(trv['shape'].values), axis=0); shape /= shape.sum()
    # W: 다른 투어 저녁들을 실제 출차 시작으로 놓고 가장 잘 맞는 걷는 시간
    W, C = min(WS, key=lambda wc: np.mean([tv(pred_share(kde([q.onset], bw=0.1), q.st, squeeze(shape, wc[1]), wc[0], ACT[q.d][0]), share(ACT[q.d][1])) for q in tr.itertuples()]))
    shape = squeeze(shape, C)
    H, tot, ext = ACT[r.d]; a = share(tot)
    same = trv[(trv.st // 60) == r.st // 60]; med = float(np.median((same if len(same) >= 5 else trv).onset))
    P = {'확률표(P0)': pred_share(onset_dist(trv, r.st, r.run, 'P0'), r.st, shape, W, H),
         '점: 시작 시각별 중앙값': pred_share(kde([med], bw=0.1), r.st, shape, W, H),
         '점: 예정+42분': pred_share(kde([(r.run if r.run == r.run else 150) + 42], bw=0.1), r.st, shape, W, H),
         '정답 시작을 안다면': pred_share(kde([r.onset], bw=0.1), r.st, shape, W, H)}
    # 과거 평균 몫: 같은 시작 시각(시)의 다른 투어 저녁 실제 몫, 시계 시간으로 맞춤
    sm = [q for q in tr.itertuples() if int(q.st) // 60 == int(r.st) // 60]
    if len(sm) < 3: sm = list(tr.itertuples())
    avg = np.zeros(len(H)); pk_clim = np.zeros(len(H))
    for q in sm:
        Hq, tq, _ = ACT[q.d]; sq = dict(zip(Hq, share(tq))); avg += np.array([sq.get(h + (int(q.st) // 60 - int(r.st) // 60) * 0, 0) if int(q.st) // 60 == int(r.st) // 60 else sq.get(h - int(r.st) // 60 + int(q.st) // 60, 0) for h in H])
        vq = np.array([sq.get(h - int(r.st) // 60 + int(q.st) // 60, 0) for h in H]); pk_clim[int(np.argmax(vq))] += 1
    P['과거 평균 몫(같은 시작 시각)'] = avg / avg.sum()
    pk = int(np.argmax(a))
    p5 = onset_dist(trv, r.st, r.run, 'P0'); pkp = np.zeros(len(H))
    for g, pg in zip(G5, p5):
        if pg > 1e-4: pkp[int(np.argmax(pred_share(kde([g], bw=0.1), r.st, shape, W, H)))] += pg
    pkp /= pkp.sum()
    PK = {'확률표(P0)': pkp, '과거 평균 몫(같은 시작 시각)': pk_clim / pk_clim.sum()}  # 과거: 다른 투어 저녁들의 최고 시간 빈도
    for k, v in P.items():
        if k not in PK: PK[k] = np.eye(len(H))[int(np.argmax(v))]
    for k, v in P.items():
        rows.append(dict(d=r.d, seq=r.seq, how=k, W=W, C=C, tv=tv(v, a), se=float(((v - a) ** 2).sum()), pk_log=float(np.log(max(PK[k][pk], 0.01))), pk_brier=float(((PK[k] - np.eye(len(H))[pk]) ** 2).sum()), hit=int(np.argmax(v) == pk), p_peak=float(v[pk]), clean=not small_same(r.d),
                         st=int(r.st), peak_h=H[pk], pred_peak_h=H[int(np.argmax(v))]))
R = pd.DataFrame(rows)
def boot(a, b, g, n=4000):
    us = np.unique(g); rng = np.random.default_rng(1); out = []
    idx = {u: np.where(g == u)[0] for u in us}
    for _ in range(n):
        m = np.concatenate([idx[u] for u in rng.choice(us, len(us))]); out.append(a[m].mean() - b[m].mean())
    return np.percentile(out, [2.5, 97.5]), np.percentile(out, [0.5, 99.5]), 2 * min(np.mean(np.array(out) >= 0), np.mean(np.array(out) <= 0))
for title, X in (('전체', R), ('같은 저녁 다른 공연장 공연 없음', R[R.clean])):
    print('\n== %s (%d저녁) — 시간대 몫 차이 TV(낮을수록 좋음), 가장 붐빈 시간 맞힘, 그 시간에 준 몫' % (title, X.d.nunique()))
    for k in P:
        x = X[X.how == k]; print('  %-24s TV %.3f | 제곱오차 %.3f | 맞힘 %3.0f%% | 가장 혼잡한 시간 확률: 로그 %.2f, Brier %.3f' % (k, x.tv.mean(), x.se.mean(), 100 * x.hit.mean(), x.pk_log.mean(), x.pk_brier.mean()))
    A = X[X.how == '확률표(P0)'].reset_index(drop=True)
    for k in ('점: 시작 시각별 중앙값', '점: 예정+42분', '과거 평균 몫(같은 시작 시각)', '정답 시작을 안다면'):
        Bq = X[X.how == k].reset_index(drop=True)
        for m, lab in (('tv', 'TV'), ('se', '제곱오차'), ('pk_brier', '최고시간 Brier')):
            ci, ci99, p = boot(A[m].values, Bq[m].values, A.seq.values)
            print('  확률표 − %-22s %-10s %+.3f (95%% %+.3f ~ %+.3f, p=%.3f)' % (k, lab, A[m].mean() - Bq[m].mean(), *ci, p))
print('\n고른 걷는 시간 W(주차 출차 시작 → 역 승차, 음수면 사람이 먼저): 중앙값 %+d분, 범위 %+d~%+d분 | 모양 압축 중앙값 %.2f' % (R.W.median(), R.W.min(), R.W.max(), R.C.median()))
# 역별 몫: 다른 투어 중앙값으로
st_rows = []
for r in E.itertuples():
    tr = E[E.seq != r.seq]
    def sh(d): H, tot, ext = ACT[d]; v = np.array([max(ext[s].clip(0, None).sum(), 0) for s in STATIONS]); return v / v.sum()
    pr = np.median(np.vstack([sh(q.d) for q in tr.itertuples()]), axis=0); pr /= pr.sum(); st_rows.append((r.seq, tv(pr, sh(r.d)), sh(r.d)))
print('역별 몫(공연 뒤 늘어난 승차): 실제 중앙값 ' + ', '.join('%s %.0f%%' % (s, 100 * np.median([x[2][i] for x in st_rows])) for i, s in enumerate(STATIONS)) +
      ' | 다른 투어 중앙값으로 맞히면 TV %.3f' % np.mean([x[1] for x in st_rows]))
# 예: 19시 시작 저녁의 시간대 몫 평균(실제 vs 확률표)
for sth in (17, 18, 19):
    x = [ACT[r.d] for r in E.itertuples() if int(r.st) // 60 == sth]
    if not x: continue
    Hs = list(range(sth + 1, 25)); m = np.mean([[dict(zip(H, share(t))).get(h, 0) for h in Hs] for H, t, _ in x], axis=0)
    print('  %d시 시작 %d저녁 실제 평균 몫: ' % (sth, len(x)) + ', '.join('%d시대 %.0f%%' % (h, 100 * v) for h, v in zip(Hs, m)))
R.to_csv('checks/station_split_backtest.csv', index=False)
