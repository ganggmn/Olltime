import sys, json, numpy as np, pandas as pd, os
exec(open(os.path.expanduser('~/bt/exit_alarm.py')).read().split("rules = [")[0])
for name, th, n, ew in [('M8', None, None, None), ('N2', 120, 2, 'E1'), ('N1', 120, 1, 'E1')]:
    R[name] = R['fire0'] if th is None else [fire_rule(r, th, n, ew) for _, r in R.iterrows()]
def per(col):
    rows = []
    for _, q in R.iterrows():
        f = q[col]; bad = 0; iou = np.nan; e = [np.nan] * 3
        if f is None or f != f: bad = int(q.hasbusy)
        elif not q.hasbusy: bad = 1
        else:
            bad = int(f < q.bs - 20)
            Tt = R[(R.tour != q.tour) & R[col].notna()]; TB = Tt[Tt.hasbusy]
            o = (np.median(TB.bs - TB[col]), np.median(Tt.pk - Tt[col]), np.median(TB.be - TB[col]))
            bs, pk, be = f + o[0], f + o[1], f + o[2]; e = [abs(bs - q.bs), abs(pk - q.pk), abs(be - q.be)]
            a0, a1, b0, b1 = bs, be + 10, q.bs, q.be + 10; inter = max(0, min(a1, b1) - max(a0, b0)); uni = max(a1, b1) - min(a0, b0); iou = inter / uni
        rows.append(dict(tour=q.tour, bad=bad, iou=iou, ebs=e[0], epk=e[1], ebe=e[2], lead=(f - q.bs) if (f == f and f is not None and q.hasbusy) else np.nan))
    return pd.DataFrame(rows)
A = {k: per(k) for k in ('M8', 'N2', 'N1')}
tours = R.tour.unique(); rng = np.random.default_rng(7)
def boot(stat):
    obs = stat(np.arange(len(R))); bs = []
    ti = {t: np.where(R.tour.values == t)[0] for t in tours}
    for _ in range(4000):
        idx = np.concatenate([ti[t] for t in rng.choice(tours, len(tours))]); bs.append(stat(idx))
    return round(float(obs), 3), [round(float(np.nanpercentile(bs, 2.5)), 3), round(float(np.nanpercentile(bs, 97.5)), 3)]
out = {}
for k in ('N2', 'N1'):
    a, b = A[k], A['M8']
    out[k + '−M8'] = dict(
        iou=boot(lambda i: np.nanmean(a.iou.values[i]) - np.nanmean(b.iou.values[i])),
        bad=boot(lambda i: a.bad.values[i].mean() - b.bad.values[i].mean()),
        start_hit20=boot(lambda i: np.nanmean(a.ebs.values[i] <= 20) - np.nanmean(b.ebs.values[i] <= 20)),
        peak_hit20=boot(lambda i: np.nanmean(a.epk.values[i] <= 20) - np.nanmean(b.epk.values[i] <= 20)),
        end_hit20=boot(lambda i: np.nanmean(a.ebe.values[i] <= 20) - np.nanmean(b.ebe.values[i] <= 20)))
for k, a in A.items():
    out[k] = dict(iou=round(float(a.iou.mean()), 3), bad=int(a.bad.sum()), n=len(a), lead_med=float(np.nanmedian(a.lead)), lead_p10=float(np.nanpercentile(a.lead, 10)), lead_p90=float(np.nanpercentile(a.lead, 90)),
                  start_hit20=round(float(np.nanmean(a.ebs <= 20)) * 100), peak_hit20=round(float(np.nanmean(a.epk <= 20)) * 100), end_hit20=round(float(np.nanmean(a.ebe <= 20)) * 100))
# 울림 뒤 간격(2025 전체)
for k in ('M8', 'N2', 'N1'):
    T = R[R[k].notna()]; TB = T[T.hasbusy]
    out[k]['offsets'] = dict(bs=float(np.median(TB.bs - TB[k])), pk=float(np.median(T.pk - T[k])), be=float(np.median(TB.be - TB[k])))
    out[k]['ramp_ok'] = None
# 오르막이 느린 저녁(혼잡 시작 칸 앞 20분 순유출이 이미 θ의 40% 넘음)에서 M8 늦음
slow = []
for i, q in R.iterrows():
    if not q.hasbusy: continue
    j = int(q.bs // 5); pre = q.n5[max(0, j - 4):j].sum() / 2  # 앞 20분 평균 10분 순유출
    slow.append((pre, A['M8'].lead[i], A['N2'].lead[i]))
S = pd.DataFrame(slow, columns=['pre', 'm8', 'n2']); q3 = S.pre.quantile(0.67)
out['slow_ramp'] = dict(thr=float(q3), m8_lead_med_slow=float(S[S.pre >= q3].m8.median()), m8_lead_med_fast=float(S[S.pre < q3].m8.median()), n2_lead_med_slow=float(S[S.pre >= q3].n2.median()), n2_lead_med_fast=float(S[S.pre < q3].n2.median()), n_slow=int((S.pre >= q3).sum()))
json.dump(out, open(os.path.expanduser('~/bt/exit_alarm_boot.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
