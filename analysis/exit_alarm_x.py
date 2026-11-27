import os, json, numpy as np, pandas as pd
exec(open(os.path.expanduser('~/bt/exit_alarm_boot.py')).read().split("A = {k: per(k)")[0])
on = {e['d']: e['onset'] for e in EV}
R['onset'] = R.d.map(on)
x = (R.N2 - R.onset).dropna(); x8 = (R.M8 - R.onset).dropna()
TB = R[R.hasbusy & R.N2.notna()]
q = lambda v: [float(np.percentile(v, 10)), float(np.median(v)), float(np.percentile(v, 90))]
out = dict(N2_minus_onset=q(x), M8_minus_onset=q(x8), N2_bs=q(TB.bs - TB.N2), N2_pk=q(R[R.N2.notna()].pk - R[R.N2.notna()].N2), N2_be=q(TB.be - TB.N2), dur=q(TB.be - TB.bs))
d0 = json.load(open(os.path.expanduser('~/bt/exit_alarm_boot.json'))); d0['ranges'] = out; json.dump(d0, open(os.path.expanduser('~/bt/exit_alarm_boot.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out))
