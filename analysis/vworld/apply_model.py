"""가상 세계 관측값만으로 우리 모델을 만들고 적용해, 가상 정답(10분 구간 인원)과 비교해요.
모델이 보는 것: 과거 40저녁·공연 없는 날 40일의 주차 5분 순유출, 역 1시간 승차, 시작 시각, 적힌 공연 시간, 관객 수 / 오늘 저녁의 시작 시각·적힌 시간·관객 수(+ 'D'는 그날 주차).
모델이 모르는 것: 진짜 끝, 사람마다 늦게 나오는 정도, 차 늦게 출발, 길이 붐비면 느려짐, 개찰구 줄, 버스·택시 손님이 S1을 지나는 것.
방식: A 확률표(과거 출차 시작 분포) / B 점(같은 시작 시각 중앙값) / C 점(적힌 시간 + 과거 지연 중앙값) / D 그날 주차로 잡은 출차 시작(실제 끝을 아는 경우)
      + E 과거 평균 몫(1시간 끝점만). 걷는 시간 W·사람 모양 압축 C는 과거 저녁의 역 1시간 승차로 골라요. 구간은 지도상 거리 ÷ 1.25m/s(붐빔 모름).
사용: data 폴더에서 python3 ../analysis/vworld/apply_model.py"""
import os, pickle, numpy as np, pandas as pd, json
D = 'checks/vworld'; Hh = pickle.load(open(f'{D}/hist.pkl', 'rb')); HIST, NS = Hh['hist'], Hh['noshow']
TEST = pickle.load(open(f'{D}/test1.pkl', 'rb')) + pickle.load(open(f'{D}/test2.pkl', 'rb'))
STRESS = pickle.load(open(f'{D}/stress.pkl', 'rb')); TONIGHT = pickle.load(open(f'{D}/tonight.pkl', 'rb'))
G5 = np.arange(0, 360, 5); NS_ = 36; TAU1, TAU2 = 8, 5  # 분: 역에서 거꾸로 S1 시작·S2 시작까지(600m, 350m ÷ 75m/분)
BP = {w: np.median([n['park5'] for n in NS if n['wk'] == w], axis=0) for w in ('평일', '주말')}
BS = {w: np.median([n['stn_hour'] for n in NS if n['wk'] == w], axis=0) for w in ('평일', '주말')}
def kde(v, bw=10.0):
    v = np.atleast_1d(np.asarray(v, float)); w = np.exp(-0.5 * ((G5[:, None] - v[None]) / bw) ** 2).sum(1); return w / w.sum()
def onset_of(o):
    ex = o['park5'] - BP[o['wk']]; lo, hi = (o['st'] + 40) // 5, (o['st'] + 360) // 5; sm = np.convolve(ex, np.ones(3) / 3, 'same')
    pk = lo + int(np.argmax(sm[lo:hi])); thr = 0.3 * sm[pk]; i = pk
    while i > lo and sm[i - 1] >= thr: i -= 1
    return i * 5 - o['st']
def shape_of(o, on):
    ex = np.clip(o['park5'] - BP[o['wk']], 0, None); b = (o['st'] + on) // 5; s = ex[b: b + 24]; return s / s.sum()
def squeeze(sh, c):
    x = np.arange(len(sh)) * 5.0; v = np.interp(x / c, x, sh, right=0); return v / v.sum()
def flow(p5, st, sh, W, vol):  # 1분마다 역 승차(사람/분)
    f = np.zeros(2000)
    for g, pg in zip(G5, p5):
        if pg < 1e-5: continue
        for j, sj in enumerate(sh):
            a = int(st + g + 5 * j + W); f[a: a + 5] += vol * pg * sj / 5
    return f
def hourly(f, H): return np.array([f[60 * h: 60 * h + 60].sum() for h in H])
def extra(o): H = list(range(o['st'] // 60 + 1, 25)); return H, np.array([o['stn_hour'][h] - BS[o['wk']][h] for h in H])
sh_ = lambda v: (lambda c: c / c.sum() if c.sum() > 0 else c)(np.clip(v, 0, None))
tv = lambda a, b: 0.5 * np.abs(sh_(a) - sh_(b)).sum()
# ---- 과거로 모델 만들기
ON = [onset_of(o) for o, _ in HIST]
SH = np.median(np.vstack([shape_of(o, on) for (o, _), on in zip(HIST, ON)]), axis=0); SH /= SH.sum()
VOL = float(np.median([np.clip(extra(o)[1], 0, None).sum() / o['N'] for o, _ in HIST]))
best = min(((w, c) for w in range(-30, 35, 5) for c in (1.0, 0.75, 0.5, 0.25)),
           key=lambda wc: np.mean([tv(hourly(flow(kde([on], 0.1), o['st'], squeeze(SH, wc[1]), wc[0], 1.0), extra(o)[0]), extra(o)[1]) for (o, _), on in zip(HIST, ON)]))
W, C = best; SHC = squeeze(SH, C); LAG = float(np.median([on - o['run'] for (o, _), on in zip(HIST, ON)]))
true_on = [t['end'] - o['st'] for o, t in HIST]
print('과거 40저녁에서 고른 것: 걷는 시간 W %+d분, 사람 모양 압축 %.2f, 관객 1명당 늘어난 역 승차 %.2f, 적힌 시간 뒤 출차 시작 중앙값 %+.0f분' % (W, C, VOL, LAG))
print('  (가상 정답과 대조: 주차로 잡은 출차 시작 − 진짜 끝 중앙값 %+.0f분, 진짜 지하철 손님/관객 %.2f)' % (np.median(np.array(ON) - np.array(true_on)), np.median([t['n_sub'] / o['N'] for o, t in HIST])))
def seg_pred(f, st):
    s2 = np.array([f[st + 10 * k + TAU2: st + 10 * k + 10 + TAU2].sum() for k in range(NS_)]); s1 = np.array([f[st + 10 * k + TAU1: st + 10 * k + 10 + TAU1].sum() for k in range(NS_)])
    occ_min = np.array([f[m + 1: m + 1 + TAU2].sum() for m in range(len(f) - 10)]); occ = np.array([occ_min[st + 10 * k: st + 10 * k + 10].mean() for k in range(NS_)])
    return s1, s2, occ
def predict(o, how):
    st = o['st']; same = [on for (h, _), on in zip(HIST, ON) if h['st'] // 60 == st // 60]
    p5 = {'A 확률표': kde(ON), 'B 점(시작 시각별 중앙값)': kde([np.median(same if len(same) >= 3 else ON)], 0.1), 'C 점(적힌 시간+과거 지연)': kde([o['run'] + LAG], 0.1),
          'D 실제 끝 안다면(그날 주차)': kde([onset_of(o)], 0.1)}[how]
    f = flow(p5, st, SHC, W, VOL * o['N']); s1, s2, occ = seg_pred(f, st)
    band = crowd = None
    if how == 'A 확률표':  # 시나리오마다 → 10·90% 범위, S2 혼잡(1㎡당 1명 이상) 확률
        S2s, Ps, CR = [], [], []
        for g, pg in zip(G5, p5):
            if pg < 1e-4: continue
            fg = flow(kde([g], 0.1), st, SHC, W, VOL * o['N']); _, s2g, occg = seg_pred(fg, st); S2s.append(s2g); Ps.append(pg); CR.append(occg / (350 * 6.0) >= 1.0)
        S2s, Ps, CR = np.array(S2s), np.array(Ps) / sum(Ps), np.array(CR)
        o_ = np.argsort(S2s, axis=0); band = np.zeros((2, NS_))
        for k in range(NS_):
            cs = np.cumsum(Ps[o_[:, k]]); band[0, k] = S2s[o_[np.searchsorted(cs, 0.1), k], k]; band[1, k] = S2s[o_[min(np.searchsorted(cs, 0.9), len(cs) - 1), k], k]
        crowd = (Ps[:, None] * CR).sum(0)
    else: crowd = (occ / (350 * 6.0) >= 1.0).astype(float)
    return dict(f=f, s1=s1, s2=s2, occ=occ, band=band, crowd=crowd)
def past_avg(o):
    H, _ = extra(o); v = np.zeros(len(H))
    for h, _ in HIST:
        if h['st'] // 60 != o['st'] // 60: continue
        Hh_, e = extra(h); d = dict(zip(Hh_, sh_(e))); v += np.array([d.get(x, 0) for x in H])
    return v
K = np.arange(6, 36)  # 시작 뒤 60~360분
acc = lambda p, t: 100 * (1 - np.abs(p[K] - t[K]).sum() / max(t[K].sum(), 1))
METH = ['A 확률표', 'B 점(시작 시각별 중앙값)', 'C 점(적힌 시간+과거 지연)', 'D 실제 끝 안다면(그날 주차)']
def score(SET):
    rows = []
    for i, (o, t) in enumerate(SET):
        H, ex = extra(o)
        for m in METH:
            p = predict(o, m); pk_t, pk_p = int(np.argmax(t['s2_in'])), int(np.argmax(p['s2']))
            r = dict(i=i, how=m, s2=acc(p['s2'], t['s2_in']), s1=acc(p['s1'], t['s1_in']), occ=acc(p['occ'], t['s2_occ']), hit=int(pk_p == pk_t), near=int(abs(pk_p - pk_t) <= 1),
                     hour_tv=tv(hourly(p['f'], H), ex), crowd_br=float(np.mean((p['crowd'][K] - (t['s2_rho'][K] >= 1.0)) ** 2)),
                     rho_pred=float((p['occ'][K] / (350 * 6.0)).max()), rho_true=float(t['s2_rho'][K].max()), vol_ratio=float(p['s2'].sum() / max(t['s2_in'].sum(), 1)))
            if p['band'] is not None: r['peak_in80'] = int(p['band'][0, pk_t] <= t['s2_in'][pk_t] <= p['band'][1, pk_t])
            if p['band'] is not None:
                live = K[(t['s2_in'][K] > 20) | (p['s2'][K] > 20)]; r['cover80'] = float(np.mean((t['s2_in'][live] >= p['band'][0, live]) & (t['s2_in'][live] <= p['band'][1, live])))
            rows.append(r)
        rows.append(dict(i=i, how='E 과거 평균 몫(1시간)', hour_tv=tv(past_avg(o), ex)))
    return pd.DataFrame(rows)
def boot(a, b, n=4000):
    rng = np.random.default_rng(0); d = a - b; m = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(n)]; return d.mean(), np.percentile(m, [2.5, 97.5])
def report(R, title):
    print('\n== %s (%d저녁) — 10분 구간 정확도는 높을수록, 1시간 끝점 TV·혼잡 Brier는 낮을수록 좋음' % (title, R.i.nunique()))
    print('  %-28s %9s %9s %9s %8s %8s %9s %11s %7s' % ('방식', 'S2 들어옴', 'S2 인원', 'S1 들어옴', '최고칸', '±10분', '역1시간TV', '최고밀도 예측/정답', '80%범위'))
    for m in METH + ['E 과거 평균 몫(1시간)']:
        x = R[R.how == m]
        if m.startswith('E'): print('  %-28s %9s %9s %9s %8s %8s %9.3f' % (m, '-', '-', '-', '-', '-', x.hour_tv.mean())); continue
        print('  %-28s %8.1f%% %8.1f%% %8.1f%% %7.0f%% %7.0f%% %9.3f %5.2f / %4.2f %7s' % (m, x.s2.mean(), x.occ.mean(), x.s1.mean(), 100 * x.hit.mean(), 100 * x.near.mean(), x.hour_tv.mean(), x.rho_pred.median(), x.rho_true.median(),
              '%.0f%%' % (100 * x.cover80.mean()) if 'cover80' in x and x.cover80.notna().any() else '-'))
    a = R[R.how == 'A 확률표']; print('  A 확률표: 정답 최고 칸이 80%% 범위 안에 든 저녁 %.0f%% | 그 칸 바깥(나머지 칸) 포함 전체 %.0f%%' % (100 * a.peak_in80.mean(), 100 * a.cover80.mean()))
    d = R[R.how == 'D 실제 끝 안다면(그날 주차)']; cr = d[d.rho_true >= 1.0]
    print('  1㎡당 1명 넘게 붐빈 저녁 %d개 중 모델(D)도 1명 넘는다고 한 저녁 %d개 | 모든 방식 S2 총인원 예측/정답 중앙값 %.2f' % (len(cr), int((cr.rho_pred >= 1.0).sum()), R[R.how == 'D 실제 끝 안다면(그날 주차)'].vol_ratio.median()))
    A = R[R.how == 'A 확률표'].set_index('i')
    for m in METH[1:]:
        B = R[R.how == m].set_index('i'); d, ci = boot(A.s2.values, B.s2.values)
        print('  A − %-26s S2 들어옴 10분 정확도 %+.1f%%p (95%% %+.1f ~ %+.1f)' % (m, d, *ci))
    E_ = R[R.how == 'E 과거 평균 몫(1시간)'].set_index('i'); d, ci = boot(A.hour_tv.values, E_.hour_tv.values)
    print('  A − E 역 1시간 TV %+.3f (95%% %+.3f ~ %+.3f)' % (d, *ci))
    for m in ('A 확률표', 'D 실제 끝 안다면(그날 주차)'):
        x = R[R.how == m]; rho = pd.Series(x.hour_tv.values).corr(pd.Series(x.s2.values), method='spearman')
        good = x[x.hour_tv <= x.hour_tv.quantile(0.25)]; bad = x[x.hour_tv >= x.hour_tv.quantile(0.75)]
        print('  %s: 역 1시간이 잘 맞은 저녁(상위 25%%)의 S2 10분 정확도 %.1f%% vs 못 맞은 저녁(하위 25%%) %.1f%% (순위상관 %.2f)' % (m, good.s2.mean(), bad.s2.mean(), rho))
    return R
R1 = report(score(TEST), '시험 100저녁(과거와 같은 세계)')
R2 = report(score(STRESS), '가정 깨기 30저녁(길 폭 3m, 개찰구 1분 130명, 차 40% 늦게, 30% 오래 남음 — 모델은 모름)')
# ---- 오늘 밤(14,000명, 19:00, 적힌 130분, 진짜 끝 21:32, 차 30% 늦게)
o, t = TONIGHT[0]; P = {m: predict(o, m) for m in METH}; ex_h = extra(o)
print('\n== 오늘 밤 가상 저녁: 관객 %d명, 19:00 시작, 진짜 끝 %02d:%02d, 지하철 손님 %d명, 차 %d대' % (o['N'], *divmod(int(t['end']), 60), t['n_sub'], t['ncar']))
print('  모델이 그날 주차로 잡은 출차 시작: %02d:%02d' % divmod(19 * 60 + onset_of(o), 60))
print('  시각    S2정답  A확률표(10~90%%)        B점   D실제끝 | S2인원 정답 D | 밀도 정답 / A혼잡확률')
for k in range(12, 27):
    print('  %02d:%02d %6.0f %6.0f (%5.0f~%5.0f) %6.0f %6.0f | %6.0f %6.0f | %.2f / %.2f' % (*divmod(19 * 60 + 10 * k, 60), t['s2_in'][k], P['A 확률표']['s2'][k], *P['A 확률표']['band'][:, k], P['B 점(시작 시각별 중앙값)']['s2'][k],
          P['D 실제 끝 안다면(그날 주차)']['s2'][k], t['s2_occ'][k], P['D 실제 끝 안다면(그날 주차)']['occ'][k], t['s2_rho'][k], P['A 확률표']['crowd'][k]))
for m in METH: print('  %-28s S2 10분 정확도 %.1f%%, 역 1시간 TV %.3f' % (m, acc(P[m]['s2'], t['s2_in']), tv(hourly(P[m]['f'], ex_h[0]), ex_h[1])))
json.dump(dict(tonight={k: [float(x) for x in v] for k, v in dict(truth=t['s2_in'], A=P['A 확률표']['s2'], A10=P['A 확률표']['band'][0], A90=P['A 확률표']['band'][1],
              B=P['B 점(시작 시각별 중앙값)']['s2'], D=P['D 실제 끝 안다면(그날 주차)']['s2'], occ_truth=t['s2_occ'], occD=P['D 실제 끝 안다면(그날 주차)']['occ'], rho=t['s2_rho'], crowdA=P['A 확률표']['crowd']).items()},
               W=W, C=C, VOL=VOL, LAG=LAG), open(f'{D}/result.json', 'w'), ensure_ascii=False)
pd.concat([R1.assign(set='test'), R2.assign(set='stress')]).to_csv(f'{D}/scores.csv', index=False)
