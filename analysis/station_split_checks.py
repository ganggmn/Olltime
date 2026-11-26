"""station_split_backtest가 '의미 있는 검증'인지 점검해요(2026-11-27).
A 시각 칸 맞춤: 5호선과 9호선의 공연 뒤 최고 시간이 같은지
B 시험의 힘: 양성 대조(그 저녁의 실제 끝) vs 음성 대조(같은 시작 시각 다른 저녁의 실제 끝을 빌려 씀)
C 저녁별 정보가 있는 방식: P3(같은 공연 전날의 실제 출차 시작)으로 둘째 날부터 과거 평균을 이기는지
D 바닥 정의 바꾸기: 바닥 빼지 않음 / 평일 공연 없는 날만
E 결과를 보고 바꾼 설정(걷는 시간 음수 허용, 모양 압축): 처음 설정(W 0~40, 압축 없음)으로 다시
F 여러 번 비교 보정(홀름), G 가려낼 수 있는 가장 작은 차이"""
import os, sys, numpy as np, pandas as pd
__file__ = os.path.abspath(__file__); HERE = os.path.dirname(__file__)
src = open(os.path.join(HERE, 'station_split_backtest.py'), encoding='utf-8').read()
exec(src.split("WS = [(w, c)")[0].replace("HERE = os.path.dirname(os.path.abspath(__file__)); ", ""))
def boot(a, b, g, n=4000, seed=1):
    us = np.unique(g); rng = np.random.default_rng(seed); idx = {u: np.where(g == u)[0] for u in us}; out = []
    for _ in range(n):
        m = np.concatenate([idx[u] for u in rng.choice(us, len(us))]); out.append(a[m].mean() - b[m].mean())
    out = np.array(out); return a.mean() - b.mean(), np.percentile(out, [2.5, 97.5]), 2 * min((out >= 0).mean(), (out <= 0).mean())
# ---- A
print('== A 시각 칸 맞춤(5호선 vs 9호선 올림픽공원역, 공연 뒤 늘어난 승차 최고 시간)')
same = n = 0
for d in E.d:
    H, tot, ext = ACT[d]; a5, a9 = ext.get('올림픽공원(5)'), ext.get('올림픽공원(9)')
    if a5 is None or a9 is None or a5.clip(0).sum() < 200 or a9.clip(0).sum() < 200: continue
    n += 1; same += int(np.argmax(a5) == np.argmax(a9))
print('  최고 시간이 같은 저녁 %d/%d' % (same, n))
# ---- 공통 예측기
def run(E_, act, WS, label, extra=None):
    rows = []
    for r in E_.itertuples():
        tr = E_[E_.seq != r.seq]; trv = EVN[EVN.seq != r.seq]
        shape0 = np.median(np.vstack(trv['shape'].values), axis=0); shape0 /= shape0.sum()
        W, C = min(WS, key=lambda wc: np.mean([tv(pred_share(kde([q.onset], bw=0.1), q.st, squeeze(shape0, wc[1]), wc[0], act[q.d][0]), share(act[q.d][1])) for q in tr.itertuples()]))
        shape = squeeze(shape0, C); H, tot, _ = act[r.d]; a = share(tot); pk = int(np.argmax(a))
        sm = [q for q in tr.itertuples() if int(q.st) // 60 == int(r.st) // 60] or list(tr.itertuples())
        avg = np.zeros(len(H)); pkc = np.zeros(len(H))
        for q in sm:
            Hq, tq, _ = act[q.d]; sq = dict(zip(Hq, share(tq))); vq = np.array([sq.get(h - int(r.st) // 60 + int(q.st) // 60, 0) for h in H]); avg += vq; pkc[int(np.argmax(vq))] += 1
        def peakprob(p5):
            v = np.zeros(len(H))
            for g, pg in zip(G5, p5):
                if pg > 1e-4: v[int(np.argmax(pred_share(kde([g], bw=0.1), r.st, shape, W, H)))] += pg
            return v / v.sum()
        F = {'확률표P0': (onset_dist(trv, r.st, r.run, 'P0'), None), '과거평균': (None, (avg / avg.sum(), pkc / pkc.sum())),
             '양성대조(그 저녁 실제 끝)': (kde([r.onset], bw=0.1), None)}
        oth = [q for q in EVN[(EVN.seq != r.seq) & ((EVN.st // 60) == r.st // 60)].itertuples()]
        if oth: F['음성대조(다른 저녁 실제 끝)'] = (kde([oth[int(r.d.replace('-', '')) % len(oth)].onset], bw=0.1), None)
        mine = EVN[(EVN.seq == r.seq) & (EVN.d < r.d)].sort_values('d')
        if len(mine) and (pd.Timestamp(r.d) - pd.Timestamp(mine.d.iloc[-1])).days <= 3:
            F['P3전날'] = (onset_dist(trv, r.st, r.run, 'P3', prev=float(mine.onset.iloc[-1])), None)
        for k, (p5, fixed) in F.items():
            if fixed is None:
                v = pred_share(p5, r.st, shape, W, H); pp = peakprob(p5) if k in ('확률표P0', 'P3전날') else np.eye(len(H))[int(np.argmax(v))]
            else: v, pp = fixed
            rows.append(dict(d=r.d, seq=r.seq, how=k, prev=bool('P3전날' in F), tv=tv(v, a), se=float(((v - a) ** 2).sum()), br=float(((pp - np.eye(len(H))[pk]) ** 2).sum())))
    R = pd.DataFrame(rows); return R
def report(R, title, pairs):
    print('\n== ' + title)
    for k in R.how.unique():
        x = R[R.how == k]; print('  %-26s n=%2d  TV %.3f  제곱오차 %.3f  최고시간 Brier %.3f' % (k, len(x), x.tv.mean(), x.se.mean(), x.br.mean()))
    out = []
    for a_, b_, sub in pairs:
        X = R[R.prev] if sub else R
        A = X[X.how == a_].set_index('d'); B = X[X.how == b_].set_index('d'); dd = A.index.intersection(B.index); A, B = A.loc[dd], B.loc[dd]
        for m in ('tv', 'se', 'br'):
            dlt, ci, p = boot(A[m].values, B[m].values, A.seq.values); out.append((a_, b_, m, dlt, ci, p, len(dd)))
            print('  [%s] − [%s] %-3s %+.3f (95%% %+.3f ~ %+.3f, p=%.3f, %d저녁)' % (a_, b_, m, dlt, *ci, p, len(dd)))
    return out
WS_main = [(w, c) for w in range(-30, 35, 5) for c in (1.0, 0.5, 0.25)]
R = run(E, ACT, WS_main, 'main')
o1 = report(R, 'B·C 본 설정(지금 결과와 같은 조건)', [('확률표P0', '과거평균', False), ('양성대조(그 저녁 실제 끝)', '과거평균', False), ('음성대조(다른 저녁 실제 끝)', '과거평균', False), ('P3전날', '과거평균', True), ('P3전날', '확률표P0', True)])
# ---- E
R2 = run(E, ACT, [(w, 1.0) for w in range(0, 45, 5)], 'orig')
report(R2, 'E 처음 설정(W 0~40분, 압축 없음)', [('확률표P0', '과거평균', False), ('P3전날', '과거평균', True)])
# ---- D 바닥 바꾸기
ACT_raw = {}
for d, (H, tot, ext) in ACT.items():
    raw = sum(np.array([ON[s][d].get(h, 0) for h in H]) for s in STATIONS); ACT_raw[d] = (H, raw, ext)
R3 = run(E, ACT_raw, WS_main, 'raw')
report(R3, 'D1 바닥 빼지 않음(공연 뒤 전체 승차의 시간대 몫)', [('확률표P0', '과거평균', False), ('P3전날', '과거평균', True)])
NOSHOW_wd = {w: NOSHOW[w] if w < 5 else NOSHOW[4] for w in range(7)}
ACT_wd = {}
for d, (H, tot, ext) in ACT.items():
    t = pd.Timestamp(d); c = sorted((abs((pd.Timestamp(x) - t).days), x) for x in NOSHOW[min(t.weekday(), 3)])[:6]
    b = sum(np.array([np.median([ON[s][x].get(h, 0) for _, x in c]) for h in H]) for s in STATIONS)
    ACT_wd[d] = (H, sum(np.array([ON[s][d].get(h, 0) for h in H]) for s in STATIONS) - b, ext)
R4 = run(E, ACT_wd, WS_main, 'wd')
report(R4, 'D2 바닥 = 공연 없는 평일(월~목) 중앙값', [('확률표P0', '과거평균', False), ('P3전날', '과거평균', True)])
# ---- F 홀름(본 설정의 비교들)
ps = sorted([(x[5], '%s−%s %s' % (x[0], x[1], x[2])) for x in o1]); m = len(ps)
print('\n== F 홀름 보정(본 설정 %d개 비교)' % m)
run_max = 0
for i, (p, lab) in enumerate(ps):
    adj = min(1, max(run_max, (m - i) * p)); run_max = adj
    if adj < 0.2: print('  %-60s p=%.3f → 보정 %.3f' % (lab, p, adj))
# ---- G
x = [o for o in o1 if o[0] == '확률표P0' and o[1] == '과거평균']
print('\n== G 가려낼 수 있는 차이: 확률표 vs 과거평균 95%% 구간 폭의 절반 — ' + ', '.join('%s ±%.3f' % (o[2], (o[4][1] - o[4][0]) / 2) for o in x))
R.to_csv('checks/station_split_checks.csv', index=False)
