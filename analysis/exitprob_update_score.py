"""퇴장 확률표 '아직 안 끝남' 고침 채점(2026-11-28): exitprob_prereg_20261127.json의 update 규칙 그대로.
판단 시각 T = 시작+150·180분. T까지의 주차만 보고, 종료 감지기(end_detect_prereg: 10분에 6.5% 감소)가
  - 안 울렸으면 출차 시작 > T−15분만 남기고 다시 나눔
  - 울렸으면 '감지 − (2025 감지−출차 시작) 분포'로 바꿈
그 표로 T 이후 칸(max(T/10, 9) ~ 32)의 10분 순유출 MAE와 출차 시작 칸 로그점수를, 미리 만든 표와 같은 칸에서 비교.
사용: data 폴더에서 python3 ../analysis/exitprob_update_score.py 2026-11-27 19:00 130 checks/exitprob_prereg_20261127.json "2026-11-27 P0" <parking.csv 복사본>"""
import os, sys, json, importlib.util, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.argv_ = sys.argv[:]; sys.argv = [sys.argv[0], 'none']
spec = importlib.util.spec_from_file_location('ep', os.path.join(HERE, 'exitprob.py')); ep = importlib.util.module_from_spec(spec); spec.loader.exec_module(ep)
spec = importlib.util.spec_from_file_location('edl', os.path.join(HERE, 'end_detect_live.py')); edl = importlib.util.module_from_spec(spec); spec.loader.exec_module(edl)
d, t, run, fn, key, pk = sys.argv_[1:7]; run = float(run); st = ep.hm(t); how = key.split()[-1]
J = json.load(open(fn)); T0 = J['tables'][key]
park = ep.load_live_park(pk); s0 = pd.Timestamp(f'{d} {t}'); sched_end = s0 + pd.Timedelta(minutes=run)
on = (edl.park_onset(park, s0) - s0) / pd.Timedelta(minutes=1); o = int(on // 10); act = ep.live_net10(park, d, st)
p_tab = np.array([r['p_onset'] for r in T0['table']]); exp_tab = np.array([r['exp_net_2026'] for r in T0['table']])
p5 = ep.onset_dist(ep.EVN, st, run, how)  # 미리 만든 표와 같은 계산(5분 칸)
p10 = ep.to10(p5)[:len(p_tab)]; same = float(np.max(np.abs(np.round(p10, 4) - p_tab)))
lagd = list(zip((ep.EVN.fire - ep.EVN.onset).dropna().values, np.ones(ep.EVN.fire.notna().sum()) / ep.EVN.fire.notna().sum()))
out = dict(day=d, key=key, onset_after_start_min=float(on), onset_slot=T0['table'][o]['slot'], table_recompute_maxdiff=same, updates=[])
for T in (150, 180):
    f = edl.fire_time(park, s0, sched_end, s0 + pd.Timedelta(minutes=T)); fired = None if f is None else (f - s0) / pd.Timedelta(minutes=1)
    q = ep.censor(p5, T, fired, lagd); _, e1, _, _, _ = ep.forecast(ep.EVN, st, run, ep.wkg(d), how, pdist=q)
    e1 = e1 * ep.K_SCALE; k = np.arange(max(T // 10, ep.W0), ep.W1); q10 = ep.to10(q)[:len(p_tab)]
    cs = np.cumsum(q10); lo, hi = np.searchsorted(cs, 0.1), np.searchsorted(cs, 0.9)
    out['updates'].append(dict(T=T, fired_by_T=fired, slots=f'{T0["table"][k[0]]["slot"]}~{T0["table"][k[-1]]["slot"]}', n_slots=int(len(k)),
        mae_prior=float(np.mean(np.abs(exp_tab[k] - act[k]))), mae_updated=float(np.mean(np.abs(e1[k] - act[k]))),
        logp_prior=float(np.log(max(p_tab[o], 1e-3))), logp_updated=float(np.log(max(q10[o], 1e-3))),
        in80_updated=bool(lo <= o <= hi), range80_updated=[T0['table'][min(lo, len(p_tab) - 1)]['slot'], T0['table'][min(hi, len(p_tab) - 1)]['slot']]))
print(json.dumps(out, ensure_ascii=False, indent=1))
