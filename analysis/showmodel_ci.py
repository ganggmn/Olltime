"""공연 날 사람 수 모델 비교마다 '우연인지 실력인지' 판정. 기준은 analysis/significance_plan.json의 F2.
사용: data 폴더에서 python3 ../analysis/showmodel_ci.py ../analysis/kopis_daily_2025.csv
kopis_size.py와 같은 예측(지난 달들만으로 배움, 3~12월, 07~23시)을 만든 뒤, 같은 공연(seq) 묶음째 재표집해요."""
import os, sys, io, json, contextlib, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from sigtest import boot_diff, holm, line, verdict
with contextlib.redirect_stdout(io.StringIO()): exec(open(os.path.join(HERE, 'kopis_size.py'), encoding='utf-8').read())
M0 = PR['M0 사이트 지금']; ALLd = sorted(M0); FIRST = [d for d in ALLd if prev_run(d) is None]; LATER = [d for d in ALLd if prev_run(d) is not None]
runlen = {}
for d in ST: runlen.setdefault(SEQ.get(d), []).append(d)
RL = {d: len(runlen.get(SEQ.get(d), [d])) for d in ST}
win = lambda d: [h for h in range(int(ST[d]) - 3, int(ST[d]) + 4) if 0 <= h < 24]
KN = {}
for d in ALLd:
    w = win(d); p = M0[d][w]; yy = INC.loc[d, w].values; KN[d] = float(np.sum(p * yy) / np.sum(p * p))
rlc = lambda d: '1~2일' if RL[d] <= 2 else '3~5일' if RL[d] <= 5 else '6일 이상'
def scaled(d, k):
    p = M0[d].copy(); w = win(d); p[w] = p[w] * k; return p
K1, K2, RT2 = {}, {}, {}
for d in ALLd:
    prior = [x for x in ALLd if x[:7] < d[:7]]; pr1 = [x for x in prior if x in TK]
    if len(pr1) >= 10 and d in TK:
        A_ = np.c_[np.ones(len(pr1)), [TK[x] / 1e4 for x in pr1]]; b = np.linalg.lstsq(A_, [KN[x] for x in pr1], rcond=None)[0]; k1 = float(np.clip(b[0] + b[1] * TK[d] / 1e4, 0.3, 3))
    else: k1 = 1.0
    K1[d] = scaled(d, k1)
    g = [KN[x] for x in prior if rlc(x) == rlc(d)]; K2[d] = scaled(d, float(np.median(g)) if len(g) >= 3 else 1.0)
    p = DAWN[d] + M0[d]; yy = Y.loc[d].values; q = p.copy()
    for h in range(2, 24): q[h] = p[h] + 0.82 * (yy[h - 2] - p[h - 2])
    RT2[d] = q - DAWN[d]
def errs(pr, ds):
    e = np.concatenate([np.abs(DAWN[d] + pr[d][H] - Y.loc[d, H].values) for d in ds]); a = np.concatenate([Y.loc[d, H].values for d in ds])
    c = np.concatenate([[str(SEQ.get(d) or d)] * len(H) for d in ds]); return e, a, c
def cmp(new, old, ds):
    en, a, c = errs(new, ds); eo, _, _ = errs(old, ds); return boot_diff(en, eo, a, c)
out = {}
print('공연 날 %d일(첫날 %d, 둘째 날 이후 %d), 같은 공연 묶음: 첫날 %d개, 둘째 날 이후 %d개' % (len(ALLd), len(FIRST), len(LATER), len({SEQ.get(d) or d for d in FIRST}), len({SEQ.get(d) or d for d in LATER})))
prim = [('둘째 날 이후: M0+같은 공연 전날 vs M0', PR['M0+같은 공연 전날'], M0, LATER), ('첫날: M0+당일 2시간 앞 vs M0', RT2, M0, FIRST)]
print('[주된 비교]'); out['primary'] = []
for lab, a, b, ds in prim:
    r = cmp(a, b, ds); print('  ' + line(lab, r)); out['primary'].append(dict(name=lab, **r, verdict=verdict(r)))
sec = [('첫날: 판매수 배율(사후) vs M0', K1), ('첫날: 공연 일수 배율 vs M0', K2), ('첫날: T 판매수 크기 vs M0', PR['T 판매수 크기']), ('첫날: A 평균 크기 vs M0', PR['A 평균 크기'])]
rs = [cmp(a, M0, FIRST) for _, a in sec]; adj = holm([r['p'] for r in rs])
print('[참고 비교, 홀름 보정 %d개]' % len(rs)); out['secondary'] = []
for (lab, _), r, pa in zip(sec, rs, adj):
    print('  ' + line(lab, r, pa)); out['secondary'].append(dict(name=lab, **r, p_holm=pa, verdict=verdict(r, pa)))
json.dump(out, open('checks/showmodel_ci.json', 'w'), ensure_ascii=False, indent=1)
