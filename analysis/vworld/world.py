"""가상 세계(정답을 아는 세계) — 모델과 다른 코드예요. 사람 하나하나를 움직여요.
돔 안: egress_sim(관람석 출구 줄, 건물 바깥문 줄, 실감형 3D 좌석·출구)로 건물 밖에 나온 시각.
밖: 지하철 손님은 S1 돔 앞~동2문(250m, 폭 12m) → S2 동2문~올림픽공원역 3번 출구(350m, 폭 6m)를 5초 단위로 걸어요.
    붐비면 느려져요(Weidmann 밀도-속도). 역에서는 개찰구 줄(1분에 cap명). 그 밖 손님(버스·택시) 절반은 S1만 지나 다른 쪽으로 가요.
차: 주차장까지 걸어감 → 일행 다 오면 2~4분 뒤 출발 + 짐 싣기 0~10분, 일부(late)는 20~40분 더 늦게(밥·기다림) → 게이트 1분에 14대.
관측(모델이 보는 것): 주차장 5분 순유출(평소 바닥 + 공연 차 + 잡음), 올림픽공원역 1시간 승차(평소 + 공연 + 잡음).
정답(모델이 못 보는 것): 진짜 끝 시각, 10분마다 S1·S2에 들어온 사람, 평균 인원, 가장 높은 밀도."""
import os, sys, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); EG = os.path.join(HERE, '..', 'egress')
_cwd = os.getcwd(); os.chdir(EG); sys.path.insert(0, EG); import egress_sim as ES; os.chdir(_cwd)
BG = np.load(os.path.join(HERE, 'bg.npz'))  # 실제 2025 평소 바닥(주차 5분 순유출, 역 1시간 승차) — 집계값
L1, W1, L2, W2 = 250.0, 12.0, 350.0, 6.0
def weidmann(rho):
    rho = np.maximum(rho, 1e-3); return np.clip(1 - np.exp(-1.913 * (1 / rho - 1 / 5.4)), 0.05, 1.0)
def draw_params(rng):
    return dict(lag=float(np.clip(rng.normal(20, 15), -5, 60)), mu=float(rng.uniform(6, 15)), early=float(rng.uniform(0.03, 0.12)), linger=float(rng.uniform(0.05, 0.2)),
                lmu=float(rng.uniform(10, 30)), car=float(rng.uniform(0.15, 0.25)), sub=float(rng.uniform(0.5, 0.65)), late=float(rng.uniform(0.1, 0.4)), cap=float(rng.uniform(200, 400)), w2=W2)
def evening(seed, st, run, N, wk, P=None):
    """st: 시작(자정부터 분), run: 적힌 공연 시간(분), N: 관객, wk: '평일' 또는 '주말'. 반환: obs(모델용), truth(채점용)"""
    rng = np.random.default_rng(seed); P = P or draw_params(rng)
    end = st + run + P['lag']
    os.chdir(EG)
    r = ES.run(N=N, start='param', mu=P['mu'], early=P['early'], linger=P['linger'], linger_mu=P['lmu'], car_share=P['car'], sub_share=P['sub'], seed=seed, ret=True)
    os.chdir(_cwd)
    mode, tb = r['mode'], r['t_bld'] / 60 + end  # 건물 밖에 나온 시각(분)
    # ---- 걷기(지하철 손님 + 그 밖 손님 절반은 S1만)
    sub = np.where(mode == 'sub')[0]; oth = np.where(mode == 'oth')[0]; oth = oth[rng.random(len(oth)) < 0.5]
    who = np.concatenate([sub, oth]); goal = np.concatenate([np.full(len(sub), L1 + L2), np.full(len(oth), L1)])
    t0 = tb[who]; v0 = rng.normal(1.25, 0.15, len(who)).clip(0.8, 1.8) * 60  # m/분
    dt = 5 / 60; T = np.arange(t0.min(), t0.max() + 90, dt); x = np.full(len(who), -1.0); t_s2 = np.full(len(who), np.nan); t_arr = np.full(len(who), np.nan)
    occ1 = np.zeros(len(T)); occ2 = np.zeros(len(T)); rho2max = np.zeros(len(T))
    for k, t in enumerate(T):
        x[(x < 0) & (t0 <= t)] = 0.0
        on1 = (x >= 0) & (x < L1); on2 = (x >= L1) & (x < goal) & (goal > L1)
        n1, n2 = on1.sum(), on2.sum(); occ1[k], occ2[k] = n1, n2; rho2 = n2 / (L2 * P['w2']); rho2max[k] = rho2
        f = np.where(on1, weidmann(n1 / (L1 * W1)), np.where(on2, weidmann(rho2), 1.0))
        moving = (x >= 0) & (x < goal); xn = x + v0 * f * dt * moving
        cross = moving & (x < L1) & (xn >= L1) & (goal > L1); t_s2[cross] = t
        done = moving & (xn >= goal); t_arr[done] = t; x = np.where(moving, xn, x)
    # ---- 역 개찰구 줄
    a = np.sort(t_arr[:len(sub)][~np.isnan(t_arr[:len(sub)])]); board = np.zeros(len(a)); last = -1e9
    for i, ta in enumerate(a): last = max(ta, last + 1 / P['cap']); board[i] = last
    # ---- 차
    c = np.where(mode == 'car')[0]; rng.shuffle(c); ncar = max(1, int(len(c) / 2.2)); groups = np.array_split(c, ncar)
    arr_car = r['t_dest'] / 60 + end
    ready = np.array([arr_car[g].max() for g in groups]) + rng.uniform(2, 4, ncar) + rng.uniform(0, 10, ncar)
    late = rng.random(ncar) < P['late']; ready[late] += rng.uniform(20, 40, late.sum()); ready.sort()
    tc = np.zeros(ncar); last = -1e9
    for i, t in enumerate(ready): last = max(t, last + 1 / 14.0); tc[i] = last
    # ---- 관측
    bgp = BG['park_wk' if wk == '평일' else 'park_we'] * rng.uniform(0.9, 1.1)
    park = bgp.copy(); idx = (tc // 5).astype(int); np.add.at(park, idx[idx < len(park)], 1)
    park = park + rng.normal(0, np.sqrt(np.abs(bgp)) + 2)
    bgs = BG['stn_wk' if wk == '평일' else 'stn_we'] * rng.uniform(0.9, 1.1)
    stn = bgs.copy(); hb = (board // 60).astype(int); np.add.at(stn, hb[hb < len(stn)], 1); stn = stn + rng.normal(0, np.sqrt(bgs) * 1.5)
    # ---- 정답(시작 기준 10분 칸, 0~360분)
    edges = st + np.arange(0, 370, 10)
    def per_slot(times): return np.histogram(times[~np.isnan(times)], bins=edges)[0].astype(float)
    def occ_slot(occ):
        return np.array([occ[(T >= a) & (T < b)].mean() if ((T >= a) & (T < b)).any() else 0.0 for a, b in zip(edges[:-1], edges[1:])])
    truth = dict(end=end, P=P, s1_in=per_slot(t0), s2_in=per_slot(t_s2[:len(sub)]), stn_in=per_slot(board), s1_occ=occ_slot(occ1), s2_occ=occ_slot(occ2),
                 s2_rho=np.array([rho2max[(T >= a) & (T < b)].max() if ((T >= a) & (T < b)).any() else 0.0 for a, b in zip(edges[:-1], edges[1:])]),
                 n_sub=len(sub), n_s1=len(who), ncar=ncar, show_board_hour=np.bincount(hb[hb < 30], minlength=30))
    obs = dict(st=st, run=run, N=N, wk=wk, park5=park, stn_hour=stn)
    return obs, truth
def noshow(seed, wk):
    rng = np.random.default_rng(seed)
    bgp = BG['park_wk' if wk == '평일' else 'park_we'] * rng.uniform(0.9, 1.1); bgs = BG['stn_wk' if wk == '평일' else 'stn_we'] * rng.uniform(0.9, 1.1)
    return dict(park5=bgp + rng.normal(0, np.sqrt(np.abs(bgp)) + 2), stn_hour=bgs + rng.normal(0, np.sqrt(bgs) * 1.5), wk=wk)
