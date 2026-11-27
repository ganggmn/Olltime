import os, json, numpy as np, pandas as pd
exec(open(os.path.expanduser('~/bt/exit_alarm_boot.py')).read().split("A = {k: per(k)")[0])
def per_h():
    rows = []
    for _, q in R.iterrows():
        f2, f8 = q['N2'], q['M8']; bad = 0; iou = np.nan; e = [np.nan] * 3
        if f2 is None or f2 != f2: bad = int(q.hasbusy)
        elif not q.hasbusy: bad = 1
        else:
            bad = int(f2 < q.bs - 20)
            Tt = R[(R.tour != q.tour)]; T2 = Tt[Tt.N2.notna()]; TB2 = T2[T2.hasbusy]
            T8 = Tt[Tt.M8.notna() & Tt.N2.notna() & (Tt.M8 >= Tt.N2)]; TB8 = T8[T8.hasbusy]
            bs = f2 + np.median(TB2.bs - TB2.N2)
            if f8 == f8 and f8 is not None and f8 >= f2:
                pk = f8 + np.median(T8.pk - T8.M8); be = f8 + np.median(TB8.be - TB8.M8)
            else:
                pk = f2 + np.median(T2.pk - T2.N2); be = f2 + np.median(TB2.be - TB2.N2)
            e = [abs(bs - q.bs), abs(pk - q.pk), abs(be - q.be)]
            a0, a1, b0, b1 = bs, be + 10, q.bs, q.be + 10; inter = max(0, min(a1, b1) - max(a0, b0)); uni = max(a1, b1) - min(a0, b0); iou = inter / uni
        rows.append(dict(bad=bad, iou=iou, ebs=e[0], epk=e[1], ebe=e[2]))
    return pd.DataFrame(rows)
A = {k: per(k) for k in ('M8', 'N2')}; A['H'] = per_h()
tours = R.tour.unique(); rng = np.random.default_rng(7)
ti = {t: np.where(R.tour.values == t)[0] for t in tours}
def boot(stat):
    obs = stat(np.arange(len(R))); bs = []
    for _ in range(4000):
        idx = np.concatenate([ti[t] for t in rng.choice(tours, len(tours))]); bs.append(stat(idx))
    return round(float(obs), 3), [round(float(np.nanpercentile(bs, 2.5)), 3), round(float(np.nanpercentile(bs, 97.5)), 3)]
a, b = A['H'], A['M8']
out = {'H': dict(iou=round(float(a.iou.mean()), 3), bad=int(a.bad.sum()), start_hit20=round(float(np.nanmean(a.ebs <= 20)) * 100), peak_hit20=round(float(np.nanmean(a.epk <= 20)) * 100), end_hit20=round(float(np.nanmean(a.ebe <= 20)) * 100)),
       'H−M8': {k: boot(fn) for k, fn in dict(iou=lambda i: np.nanmean(a.iou.values[i]) - np.nanmean(b.iou.values[i]), bad=lambda i: a.bad.values[i].mean() - b.bad.values[i].mean(),
                start_hit20=lambda i: np.nanmean(a.ebs.values[i] <= 20) - np.nanmean(b.ebs.values[i] <= 20), peak_hit20=lambda i: np.nanmean(a.epk.values[i] <= 20) - np.nanmean(b.epk.values[i] <= 20),
                end_hit20=lambda i: np.nanmean(a.ebe.values[i] <= 20) - np.nanmean(b.ebe.values[i] <= 20)).items()}}
T8 = R[R.M8.notna() & R.N2.notna() & (R.M8 >= R.N2)]; TB8 = T8[T8.hasbusy]
out['H_offsets_from_M8_after_N2'] = dict(pk=float(np.median(T8.pk - T8.M8)), be=float(np.median(TB8.be - TB8.M8)), n=len(T8))
out['M8_before_N2'] = int((R.M8.notna() & R.N2.notna() & (R.M8 < R.N2)).sum())
out['N2_to_M8_gap_med'] = float(np.median((R.M8 - R.N2).dropna()))
d0 = json.load(open(os.path.expanduser('~/bt/exit_alarm_boot.json'))); d0.update(out); json.dump(d0, open(os.path.expanduser('~/bt/exit_alarm_boot.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False))
