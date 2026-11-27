"""'피크가 있다는 걸 안다면?' 시험. 사람 모양을 주차(차) 대신 과거 저녁의 공원 인구(5분, 500명 단위) 감소로 배워요.
F  그날 주차로 잡은 출차 시작 + 공원 인구로 배운 사람 모양(붐빔 모름)
G  F + 길이 붐비면 느려짐(직선형 속도-밀도, 가상 세계의 Weidmann과 다른 식, 길 폭은 지도값)
FA 공연 전: 과거 출차 시작 확률 × 공원 인구 사람 모양(+ G와 같은 붐빔)
비교용: 앞 결과의 A(확률표, 주차 모양), D(그날 주차, 주차 모양)"""
import os, numpy as np, pandas as pd
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apply_model.py'), encoding='utf-8').read()
exec(src.split("K = np.arange(6, 36)")[0])
K = np.arange(6, 36); acc = lambda p, t: 100 * (1 - np.abs(p[K] - t[K]).sum() / max(t[K].sum(), 1))
TAUS = np.arange(-60, 120, 5)
def drop_shape(o, on):
    b0 = (o['st'] + on - 60) // 5; d = -np.diff(o['pop5'][b0: b0 + len(TAUS) + 1]); d = np.clip(d, 0, None); return d / d.sum() if d.sum() > 0 else d  # 칸 j = [b0+j, b0+j+1) 동안 줄어든 인구(2026-11-27 한 칸 밀림 고침)
SHP = np.mean(np.vstack([drop_shape(o, on) for (o, _), on in zip(HIST, ON)]), axis=0); SHP /= SHP.sum()  # 평균(2026-11-27 고침: 중앙값은 저녁마다 다른 정점 위치 때문에 모양이 뭉개짐)
pk = TAUS[int(np.argmax(SHP))]; half = TAUS[int(np.searchsorted(np.cumsum(SHP), 0.5))]
print('공원 인구로 배운 사람 모양: 주차 출차 시작 기준 가장 많이 빠지는 5분 %+d분, 절반이 빠지는 때 %+d분' % (pk, half))
print('  (가상 정답과 대조: 주차 출차 시작은 진짜 끝보다 중앙값 %+.0f분 늦음 → 진짜 끝 기준 최고 %+d분)' % (np.median(np.array(ON) - np.array(true_on)), pk + np.median(np.array(ON) - np.array(true_on))))
def flow_pop(p5, st, vol):  # 1분마다 S2(동2문)로 나가는 사람
    f = np.zeros(2000)
    for g, pg in zip(G5, p5):
        if pg < 1e-5: continue
        for tau, sj in zip(TAUS, SHP):
            a = int(st + g + tau); f[a: a + 5] += vol * pg * sj / 5
    return f
def link(fin, w, v0=75.0, L=350.0, rmax=5.4):  # S2 칸: 들어온 사람이 쌓이고, 밀도가 높을수록 느리게 빠짐(직선형)
    n = 0.0; occ = np.zeros(len(fin)); rho = np.zeros(len(fin)); sub = 8
    for m in range(len(fin)):
        for _ in range(sub):
            r_ = n / (L * w); v = v0 * max(0.05, 1 - r_ / rmax); out = min(n, n * v / L / sub); n += fin[m] / sub - out
        occ[m] = n; rho[m] = n / (L * w)
    return occ, rho
def seg(f, st, w, cong):
    s2 = np.array([f[st + 10 * k: st + 10 * k + 10].sum() for k in range(NS_)])
    if cong: occ_m, rho_m = link(f, w)
    else:
        occ_m = np.array([f[max(0, m - TAU2): m].sum() for m in range(len(f))]); rho_m = occ_m / (350 * w)
    occ = np.array([occ_m[st + 10 * k: st + 10 * k + 10].mean() for k in range(NS_)]); rho = np.array([rho_m[st + 10 * k: st + 10 * k + 10].max() for k in range(NS_)])
    return s2, occ, rho
def pred(o, t, how):
    st = o['st']; w = t['P']['w2']; vol = VOL * o['N']
    if how in ('A 확률표(주차 모양)', 'D 실제 끝(주차 모양)'):
        p = predict(o, 'A 확률표' if how.startswith('A') else 'D 실제 끝 안다면(그날 주차)'); return p['s2'], p['occ'], p['occ'] / (350 * 6.0), (p['band'], p['crowd']) if how.startswith('A') else None
    p5 = kde(ON) if how.startswith('FA') else kde([onset_of(o)], 0.1)
    f = flow_pop(p5, st, vol); s2, occ, rho = seg(f, st, w, cong=not how.startswith('F 실제'))
    extra = None
    if how.startswith('FA'):
        S, Pw, CR = [], [], []
        for g, pg in zip(G5, p5):
            if pg < 1e-4: continue
            s2g, _, rg = seg(flow_pop(kde([g], 0.1), st, vol), st, w, True); S.append(s2g); Pw.append(pg); CR.append(rg >= 1.0)
        S, Pw, CR = np.array(S), np.array(Pw) / sum(Pw), np.array(CR); o_ = np.argsort(S, axis=0); band = np.zeros((2, NS_))
        for k in range(NS_):
            cs = np.cumsum(Pw[o_[:, k]]); band[0, k] = S[o_[np.searchsorted(cs, 0.1), k], k]; band[1, k] = S[o_[min(np.searchsorted(cs, 0.9), len(cs) - 1), k], k]
        extra = (band, (Pw[:, None] * CR).sum(0))
    return s2, occ, rho, extra
M2 = ['A 확률표(주차 모양)', 'D 실제 끝(주차 모양)', 'F 실제 끝 + 공원 인구 모양', 'G 실제 끝 + 공원 인구 모양 + 붐빔', 'FA 공연 전 확률표 + 공원 인구 모양 + 붐빔']
def run(SET, title):
    rows = []
    for i, (o, t) in enumerate(SET):
        for m in M2:
            s2, occ, rho, ex = pred(o, t, m); pk_t = int(np.argmax(t['s2_in'])); pk_p = int(np.argmax(s2)); crowd_t = t['s2_rho'][K].max() >= 1.0
            r = dict(i=i, how=m, s2=acc(s2, t['s2_in']), occ=acc(occ, t['s2_occ']), hit=int(pk_p == pk_t), near=int(abs(pk_p - pk_t) <= 1), rho_p=float(rho[K].max()), rho_t=float(t['s2_rho'][K].max()),
                     crowd_t=crowd_t, crowd_p=bool(rho[K].max() >= 1.0))
            if ex is not None:
                band, cp = ex; r['peak_in80'] = int(band[0, pk_t] <= t['s2_in'][pk_t] <= band[1, pk_t]); r['p_crowd'] = float(cp[K].max())
            rows.append(r)
    R = pd.DataFrame(rows)
    print('\n== %s (%d저녁)' % (title, R.i.nunique()))
    print('  %-34s %9s %9s %7s %7s %13s %15s' % ('방식', 'S2 10분', 'S2 인원', '최고칸', '±10분', '최고밀도 예/정', '혼잡 저녁 잡음(헛경보)'))
    for m in M2:
        x = R[R.how == m]; ct = x[x.crowd_t]; cf = x[~x.crowd_t]
        print('  %-34s %8.1f%% %8.1f%% %6.0f%% %6.0f%% %6.2f / %4.2f %7d/%-3d (%d)' % (m, x.s2.mean(), x.occ.mean(), 100 * x.hit.mean(), 100 * x.near.mean(), x.rho_p.median(), x.rho_t.median(), ct.crowd_p.sum(), len(ct), cf.crowd_p.sum()))
    for m in ('A 확률표(주차 모양)', 'FA 공연 전 확률표 + 공원 인구 모양 + 붐빔'):
        x = R[R.how == m]; print('  %s: 정답 최고 칸이 80%% 범위 안 %.0f%%' % (m, 100 * x.peak_in80.mean()) + (' | 혼잡(1명/㎡) 확률: 실제 혼잡 저녁 평균 %.2f, 아닌 저녁 %.2f' % (x[x.crowd_t].p_crowd.mean(), x[~x.crowd_t].p_crowd.mean()) if 'p_crowd' in x and x.p_crowd.notna().any() else ''))
    def bt(a, b):
        rng = np.random.default_rng(0); d = a - b; m = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(4000)]; return d.mean(), np.percentile(m, [2.5, 97.5])
    for a_, b_ in (('F 실제 끝 + 공원 인구 모양', 'D 실제 끝(주차 모양)'), ('G 실제 끝 + 공원 인구 모양 + 붐빔', 'F 실제 끝 + 공원 인구 모양'), ('FA 공연 전 확률표 + 공원 인구 모양 + 붐빔', 'A 확률표(주차 모양)')):
        A_ = R[R.how == a_].sort_values('i'); B_ = R[R.how == b_].sort_values('i')
        for col, lab in (('s2', 'S2 10분 정확도'), ('occ', 'S2 인원 정확도')):
            d, ci = bt(A_[col].values, B_[col].values); print('  [%s] − [%s] %s %+.1f%%p (95%% %+.1f ~ %+.1f)' % (a_[:2].strip(), b_[:2].strip(), lab, d, *ci))
    return R
R1 = run(TEST, '같은 세계 100저녁'); R2 = run(STRESS, '가정 깨기 30저녁(개찰구 1분 130명, 차 40% 늦게, 30% 오래 남음, 길 폭 3m — 폭은 지도값으로 모델도 앎)')
o, t = TONIGHT[0]; P = {m: pred(o, t, m) for m in M2}
print('\n== 가상 오늘 밤(14,000명, 19:00, 진짜 끝 21:32)')
print('  시각   S2정답  D(주차모양)  G(인구모양+붐빔)  FA공연전(10~90%%) | S2인원 정답 G | 밀도 정답 G / FA혼잡확률')
for k in range(13, 25):
    print('  %02d:%02d %6.0f %8.0f %10.0f %10.0f (%4.0f~%4.0f) | %6.0f %6.0f | %.2f %.2f / %.2f' % (*divmod(19 * 60 + 10 * k, 60), t['s2_in'][k], P['D 실제 끝(주차 모양)'][0][k], P['G 실제 끝 + 공원 인구 모양 + 붐빔'][0][k],
          P['FA 공연 전 확률표 + 공원 인구 모양 + 붐빔'][0][k], *P['FA 공연 전 확률표 + 공원 인구 모양 + 붐빔'][3][0][:, k], t['s2_occ'][k], P['G 실제 끝 + 공원 인구 모양 + 붐빔'][1][k], t['s2_rho'][k], P['G 실제 끝 + 공원 인구 모양 + 붐빔'][2][k], P['FA 공연 전 확률표 + 공원 인구 모양 + 붐빔'][3][1][k]))
for m in M2: print('  %-34s S2 10분 정확도 %.1f%%, S2 인원 정확도 %.1f%%' % (m, acc(P[m][0], t['s2_in']), acc(P[m][1], t['s2_occ'])))
import json; json.dump({k: [float(x) for x in v] for k, v in dict(truth=t['s2_in'], D=P['D 실제 끝(주차 모양)'][0], G=P['G 실제 끝 + 공원 인구 모양 + 붐빔'][0], FA=P['FA 공연 전 확률표 + 공원 인구 모양 + 붐빔'][0],
          FA90=P['FA 공연 전 확률표 + 공원 인구 모양 + 붐빔'][3][0][1], rho_t=t['s2_rho'], rho_G=P['G 실제 끝 + 공원 인구 모양 + 붐빔'][2]).items()}, open(f'{D}/result_peak.json', 'w'))
pd.concat([R1.assign(set='test'), R2.assign(set='stress')]).to_csv(f'{D}/scores_peak.csv', index=False)
