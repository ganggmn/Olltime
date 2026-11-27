"""가상 저녁들을 만들어 저장해요(맥 data/checks/vworld). 과거 40저녁 + 공연 없는 날 40일 + 시험 100저녁 + 가정 깨기 30저녁 + 오늘 밤 1.
사용: data 폴더에서 python3 ../analysis/vworld/make_worlds.py <part>   (part: hist, test1, test2, stress, tonight)"""
import os, sys, pickle, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import world as W
OUT = os.environ.get('VW_DIR', 'checks/vworld'); os.makedirs(OUT, exist_ok=True)
def plan(seed, n):
    rng = np.random.default_rng(seed); out = []
    for i in range(n):
        st = int(rng.choice([17 * 60, 18 * 60, 19 * 60, 19 * 60 + 30], p=[.3, .35, .25, .1])); run = int(rng.choice([120, 130, 150, 170])); N = int(rng.uniform(6000, 15000))
        wk = '주말' if rng.random() < 0.8 else '평일'; out.append((seed * 1000 + i, st, run, N, wk))
    return out
part = sys.argv[1]
if part == 'hist':
    H = [(*W.evening(s, st, run, N, wk), dict(seed=s)) for s, st, run, N, wk in plan(1, 40)]
    NS = [W.noshow(5000 + i, '주말' if i % 2 else '평일') for i in range(40)]
    pickle.dump(dict(hist=[(o, t) for o, t, _ in H], noshow=NS), open(f'{OUT}/hist.pkl', 'wb'))
elif part in ('test1', 'test2'):
    pl = plan(2, 100)[:50] if part == 'test1' else plan(2, 100)[50:]
    pickle.dump([W.evening(s, st, run, N, wk) for s, st, run, N, wk in pl], open(f'{OUT}/{part}.pkl', 'wb'))
elif part == 'stress':
    out = []
    for s, st, run, N, wk in plan(3, 30):
        P = W.draw_params(np.random.default_rng(s)); P.update(w2=3.0, cap=130.0, late=0.4, linger=0.3)  # 길 폭 3m, 개찰구 1분 130명, 차 40% 늦게, 30% 남아 있음
        out.append(W.evening(s, st, run, N, wk, P))
    pickle.dump(out, open(f'{OUT}/stress.pkl', 'wb'))
elif part == 'tonight':
    P = dict(lag=22.0, mu=10.0, early=0.08, linger=0.15, lmu=20.0, car=0.2, sub=0.6, late=0.3, cap=300.0, w2=6.0)
    pickle.dump([W.evening(7, 19 * 60, 130, 14000, '주말', P)], open(f'{OUT}/tonight.pkl', 'wb'))
print(part, 'ok')
