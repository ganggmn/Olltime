"""실시간 주차를 '퇴장 시각 판정' 없이 그대로 넣는 방식(베이즈 갱신) — 가상 세계 시험.
5분마다: 출차 시작이 g분(시작 뒤)일 확률 ∝ 사전 확률(과거 분포) × 지금까지 주차 순유출이 'g일 때 기대값'과 얼마나 맞나(정규 잡음).
  기대값 = 관객 × 관객당 공연 차(과거 중앙값) × 과거 차 모양(출차 시작 기준 −60~+150분, 평균) + 평소 바닥.
  잡음 = 공연 없는 날 흔들림 + 기대값의 35%(저녁마다 모양이 달라서).
그 확률로 공원 인구로 배운 사람 모양(apply_peak)을 섞어 S2 앞으로 60분을 예측.
비교: 사전만(실시간 없음) / 임계값 감지(10분에 평소보다 40대 더 나가면 '출차 시작 = 감지 − 15분') / 사후(그날 주차 전체로 잡은 출차 시작)."""
import os, numpy as np, pandas as pd
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apply_peak.py'), encoding='utf-8').read()
exec(src.split("M2 = [")[0])
PT = np.arange(-60, 155, 5)
def car_shape(o, on):
    b0 = (o['st'] + on - 60) // 5; e = (o['park5'] - BP[o['wk']])[b0: b0 + len(PT)]; return e
E_ = np.array([car_shape(o, on) for (o, _), on in zip(HIST, ON)]); CARS = np.array([e[(PT >= -30)].clip(0).sum() for e in E_])
CV = float(np.median(CARS / np.array([o['N'] for o, _ in HIST]))); PSH = np.mean(E_ / CARS[:, None], axis=0)
SDN = float(np.std(np.concatenate([n['park5'] - BP[n['wk']] for n in NS])[200:280]))
print('과거에서: 관객 1명당 공연 차 %.3f대, 공연 없는 날 5분 흔들림 %.1f대' % (CV, SDN))
PRIOR = kde(ON)
def s2_series(o, g):  # 출차 시작 g일 때 S2 1분 유입
    return flow_pop(kde([g], 0.1), o['st'], VOL * o['N'])
def posterior(o, T):
    st = o['st']; b_lo = (st + 60) // 5; b_hi = int(T) // 5  # T 전에 끝난 칸까지
    if b_hi <= b_lo: return PRIOR.copy()
    y = (o['park5'] - BP[o['wk']])[b_lo:b_hi]; tb = np.arange(b_lo, b_hi) * 5
    ll = np.zeros(len(G5))
    for j, g in enumerate(G5):
        mu = CV * o['N'] * np.interp(tb - (st + g), PT, PSH, left=0, right=0); sd = np.sqrt(SDN ** 2 + (0.35 * mu) ** 2)
        ll[j] = -0.5 * np.sum(((y - mu) / sd) ** 2 + 2 * np.log(sd))
    p = PRIOR * np.exp(ll - ll.max()); return p / p.sum()
def fire_time(o, thr=40):
    ex = o['park5'] - BP[o['wk']]; s10 = ex + np.roll(ex, 1)
    for b in range((o['st'] + 60) // 5, (o['st'] + 360) // 5):
        if s10[b] >= thr: return (b + 1) * 5
    return None
RT = [-20, -10, 0, 5, 10, 15, 20, 30]
def run(SET, title):
    rows, alerts = [], []
    for i, (o, t) in enumerate(SET):
        st = o['st']; S = np.array([s2_series(o, g) for g in G5])  # 시나리오별 1분 유입
        slot = lambda f, a: np.array([f[a + 10 * k: a + 10 * k + 10].sum() for k in range(6)])
        true_min = np.zeros(2000); true_slots = t['s2_in']
        on_post = onset_of(o); pk_true = st + 10 * int(np.argmax(true_slots)) + 5; fire = fire_time(o)
        for dT in RT:
            T = int(round((t['end'] + dT) / 10) * 10)  # 10분 칸 경계에 맞춤
            k0 = (T - st) // 10
            if k0 < 0 or k0 + 6 > len(true_slots): continue
            truth = true_slots[k0:k0 + 6]
            post = posterior(o, T)
            preds = {'실시간 주차 그대로(베이즈)': (post[:, None] * S).sum(0), '사전만(실시간 없음)': (PRIOR[:, None] * S).sum(0)}
            if fire is not None and fire <= T: preds['임계값 감지'] = s2_series(o, fire - 15 - st)
            else: preds['임계값 감지'] = preds['사전만(실시간 없음)']
            preds['사후(그날 주차 전체)'] = s2_series(o, on_post)
            for k, f in preds.items():
                p = slot(f, T); a = 100 * (1 - np.abs(p - truth).sum() / max(truth.sum(), 1))
                rows.append(dict(i=i, dT=dT, how=k, acc=a, ahead=pk_true > T, hit=int(np.argmax(p) == np.argmax(truth)) if pk_true > T else np.nan, mass=truth.sum()))
            rows.append(dict(i=i, dT=dT, how='_post_near', acc=float(post[np.abs(G5 - on_post) <= 10].sum())))
        # 경보: 5분마다, '사람 정점이 앞으로 20분 안' 확률 ≥ 0.5가 처음 되는 때
        pk_off = TAUS[int(np.argmax(SHP))] + 2.5  # 출차 시작 기준 사람 정점(5분 칸 가운데)
        tA = None
        for T in range(int(t['end']) - 40, int(t['end']) + 45, 5):
            post = posterior(o, T); when = st + G5 + pk_off
            if post[(when >= T) & (when <= T + 20)].sum() >= 0.5: tA = T; break
        alerts.append(dict(i=i, lead=None if tA is None else pk_true - tA, fire_lead=None if fire is None else pk_true - fire))
    R = pd.DataFrame(rows); A = pd.DataFrame(alerts)
    print('\n== %s (%d저녁) — 앞으로 60분 S2 10분 정확도 / 정점이 아직 앞일 때 정점 칸 맞힘' % (title, R.i.nunique()))
    print('  %-22s ' % '진짜 끝 기준 시각' + ''.join('%14s' % ('%+d분' % d) for d in RT))
    for k in ('사전만(실시간 없음)', '임계값 감지', '실시간 주차 그대로(베이즈)', '사후(그날 주차 전체)'):
        x = R[R.how == k]; print('  %-22s ' % k + ''.join('%7.1f%% %4s' % (x[x.dT == d].acc.mean(), ('%.0f%%' % (100 * x[(x.dT == d) & x.ahead].hit.mean())) if x[(x.dT == d) & x.ahead].hit.notna().any() else '-') for d in RT))
    x = R[R.how == '_post_near']; print('  %-22s ' % '출차 시작 ±10분 확률' + ''.join('%11.2f   ' % x[x.dT == d].acc.mean() for d in RT))
    ld = A.lead.dropna(); fl = A.fire_lead.dropna()
    print('  경보(사람 정점이 20분 안일 확률 ≥ 0.5): 낸 저녁 %d/%d, 정점보다 앞선 시간 중앙 %+.0f분(10~90%% %+.0f ~ %+.0f), 정점 전에 낸 저녁 %.0f%%, 30분 넘게 이른 저녁 %d' %
          (len(ld), len(A), ld.median(), *np.percentile(ld, [10, 90]), 100 * (ld > 0).mean(), int((ld > 30).sum())))
    print('  비교: 임계값 감지는 정점보다 중앙 %+.0f분(정점 전 %.0f%%)' % (fl.median(), 100 * (fl > 0).mean()))
    return R, A
R1, A1 = run(TEST, '같은 세계 100저녁'); R2, A2 = run(STRESS, '가정 깨기 30저녁')
R1.assign(set='test').to_csv('checks/vworld/live_update.csv', index=False)
