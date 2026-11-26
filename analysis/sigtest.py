"""우연인지 실력인지 가르는 도구: 묶음 재표집 신뢰구간과 홀름 보정.
정확도 = 100 × (1 − Σ|오차| ÷ Σ실제). 두 방식의 정확도 차이(새 − 기존)를
날짜 또는 같은 공연(투어) 묶음째로 다시 뽑아 B번 계산하고, 가운데 95%·99%를 구간으로 써요.
시간 단위로 뽑지 않아요. 같은 날의 시간끼리, 같은 투어의 날끼리는 닮아서 구간이 실제보다 좁아지기 때문이에요.
판정(미리 정한 기준, analysis/significance_plan.json):
  95% 구간이 0을 끼지 않으면 'α=0.05에서 우연 아님', 99% 구간도 0을 끼지 않으면 'α=0.01에서도 우연 아님',
  0을 끼면 '차이 있다고 말할 수 없음'. 한 묶음(가족)에서 여러 비교를 하면 홀름 보정한 p로 판정해요."""
import numpy as np

B_DEFAULT = 10000


def boot_diff(err_new, err_old, actual, cluster, B=B_DEFAULT, seed=0):
    err_new, err_old, actual = (np.asarray(x, float) for x in (err_new, err_old, actual))
    cluster = np.asarray(cluster)
    keys, inv = np.unique(cluster, return_inverse=True)
    En = np.bincount(inv, weights=err_new); Eo = np.bincount(inv, weights=err_old); A = np.bincount(inv, weights=actual)
    acc = lambda E, a: 100 * (1 - E / a)
    d0 = acc(En.sum(), A.sum()) - acc(Eo.sum(), A.sum())
    rng = np.random.default_rng(seed); k = len(keys)
    idx = rng.integers(0, k, size=(B, k))
    sA = A[idx].sum(1); D = acc(En[idx].sum(1), sA) - acc(Eo[idx].sum(1), sA)
    lo95, hi95 = np.percentile(D, [2.5, 97.5]); lo99, hi99 = np.percentile(D, [0.5, 99.5])
    p = min(1.0, 2 * min((D <= 0).mean(), (D >= 0).mean())); p = max(p, 1 / B)
    return dict(new=round(float(acc(En.sum(), A.sum())), 4), old=round(float(acc(Eo.sum(), A.sum())), 4), diff=round(float(d0), 4),
                ci95=[round(float(lo95), 2), round(float(hi95), 2)], ci99=[round(float(lo99), 2), round(float(hi99), 2)], p=float(p), clusters=int(k))


def holm(ps):
    ps = np.asarray(ps, float); m = len(ps); order = np.argsort(ps); adj = np.empty(m); run = 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * ps[i])); adj[i] = run
    return adj.tolist()


def verdict(r, p_adj=None):
    p = r['p'] if p_adj is None else p_adj
    if p_adj is None:
        if r['ci99'][0] > 0 or r['ci99'][1] < 0: return 'α=0.01에서도 우연 아님'
        if r['ci95'][0] > 0 or r['ci95'][1] < 0: return 'α=0.05에서 우연 아님'
        return '차이 있다고 말할 수 없음'
    return 'α=0.01에서도 우연 아님' if p < 0.01 else 'α=0.05에서 우연 아님' if p < 0.05 else '차이 있다고 말할 수 없음'


def line(lab, r, p_adj=None):
    s = '%s: %.1f%% → %.1f%% (차이 %+.1f%%p, 95%% 구간 %+.1f ~ %+.1f, 99%% 구간 %+.1f ~ %+.1f, p=%.4f%s, 묶음 %d개) → %s' % (
        lab, r['old'], r['new'], r['diff'], r['ci95'][0], r['ci95'][1], r['ci99'][0], r['ci99'][1], r['p'],
        '' if p_adj is None else ', 홀름 보정 p=%.4f' % p_adj, r['clusters'], verdict(r, p_adj))
    return s
