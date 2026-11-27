import os, json, numpy as np, pandas as pd
exec(open(os.path.expanduser('~/bt/exit_alarm_boot.py')).read().split("A = {k: per(k)")[0])
tours = R.tour.unique(); rng = np.random.default_rng(7); ti = {t: np.where(R.tour.values == t)[0] for t in tours}
def run2(Rsub, Tpool, th2):
    """1단계 N2(120×2)로 시작, 2단계(10분 순유출 ≥ th2, 1단계 뒤)가 울리면 최대·끝을 2단계 간격으로, 아니면 1단계 간격."""
    col2 = f'S{th2}'
    rows = []
    for _, q in Rsub.iterrows():
        f1, f2 = q['N2'], q[col2]; r = dict(bad=0, iou=np.nan, ebs=np.nan, epk=np.nan, ebe=np.nan, pk_issue=np.nan)
        if f1 is None or f1 != f1: r['bad'] = int(q.hasbusy); rows.append(r); continue
        if not q.hasbusy: r['bad'] = 1; rows.append(r); continue
        r['bad'] = int(f1 < q.bs - 20)
        Tt = Tpool[Tpool.tour != q.tour]; T1 = Tt[Tt.N2.notna()]; TB1 = T1[T1.hasbusy]; T2 = Tt[Tt[col2].notna()]; TB2 = T2[T2.hasbusy]
        bs = f1 + np.median(TB1.bs - TB1.N2)
        if f2 == f2 and f2 is not None: pk = f2 + np.median(T2.pk - T2[col2]); be = f2 + np.median(TB2.be - TB2[col2]); r['pk_issue'] = f2 - q.pk
        else: pk = f1 + np.median(T1.pk - T1.N2); be = f1 + np.median(TB1.be - TB1.N2); r['pk_issue'] = f1 - q.pk
        r.update(ebs=abs(bs - q.bs), epk=abs(pk - q.pk), ebe=abs(be - q.be))
        a0, a1, b0, b1 = bs, be + 10, q.bs, q.be + 10; inter = max(0, min(a1, b1) - max(a0, b0)); uni = max(a1, b1) - min(a0, b0); r['iou'] = inter / uni
        rows.append(r)
    return pd.DataFrame(rows)
def stage2(r, th2):
    f1 = r['N2']
    if f1 is None or f1 != f1: return None
    for k in range(2, 73):
        t = 5 * k
        if t < f1: continue
        if r.n5[k - 2] + r.n5[k - 1] >= th2: return float(t)
    return None
TH2 = (150, 180, 210, 240, 270, 300)
for th2 in TH2: R[f'S{th2}'] = [stage2(r, th2) for _, r in R.iterrows()]
TR = R[R.m <= 6]; TE = R[R.m >= 7]
tab = {}
for th2 in TH2:
    a = run2(TR, TR, th2); b = run2(TE, TR, th2)
    tab[th2] = dict(train_iou=round(float(a.iou.mean()), 3), test_iou=round(float(b.iou.mean()), 3), train_end20=round(float(np.nanmean(a.ebe <= 20)) * 100), test_end20=round(float(np.nanmean(b.ebe <= 20)) * 100),
                    test_pk20=round(float(np.nanmean(b.epk <= 20)) * 100), fired2=int(R[f'S{th2}'].notna().sum()))
best2 = max(TH2, key=lambda t: tab[t]['train_iou'])
A2 = run2(R, R, best2); M8 = per('M8'); N2 = per('N2')
def boot(stat):
    obs = stat(np.arange(len(R))); bs = []
    for _ in range(4000):
        idx = np.concatenate([ti[t] for t in rng.choice(tours, len(tours))]); bs.append(stat(idx))
    return round(float(obs), 3), [round(float(np.nanpercentile(bs, 2.5)), 3), round(float(np.nanpercentile(bs, 97.5)), 3)]
cmp = {}
for nm, B in (('M8', M8), ('N2', N2)):
    cmp['2단계−' + nm] = dict(iou=boot(lambda i: np.nanmean(A2.iou.values[i]) - np.nanmean(B.iou.values[i])), end_hit20=boot(lambda i: np.nanmean(A2.ebe.values[i] <= 20) - np.nanmean(B.ebe.values[i] <= 20)),
                             peak_hit20=boot(lambda i: np.nanmean(A2.epk.values[i] <= 20) - np.nanmean(B.epk.values[i] <= 20)), start_hit20=boot(lambda i: np.nanmean(A2.ebs.values[i] <= 20) - np.nanmean(B.ebs.values[i] <= 20)))
T2 = R[R[f'S{best2}'].notna()]; TB2 = T2[T2.hasbusy]
out = dict(stage2_table=tab, best_th2_2025=best2, best_th2_2026=round(best2 * 0.649), two_stage=dict(iou=round(float(A2.iou.mean()), 3), bad=int(A2.bad.sum()), start_hit20=round(float(np.nanmean(A2.ebs <= 20)) * 100), peak_hit20=round(float(np.nanmean(A2.epk <= 20)) * 100), end_hit20=round(float(np.nanmean(A2.ebe <= 20)) * 100),
           peak_pred_issued_minus_true_peak_med=float(np.nanmedian(A2.pk_issue))), stage2_offsets=dict(pk=float(np.median(T2.pk - T2[f'S{best2}'])), be=float(np.median(TB2.be - TB2[f'S{best2}']))), compare=cmp)
d0 = json.load(open(os.path.expanduser('~/bt/exit_alarm_boot.json'))); d0['two_stage'] = out; json.dump(d0, open(os.path.expanduser('~/bt/exit_alarm_boot.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False))
