"""'조용필 작년 기록 반영판' 퇴장 확률표 — 오늘 아침 고정한 P0·P3 표는 그대로 두고, 별도로 공연 전에 고정해요(2026-11-27).
근거: 2024 '조용필 & 위대한탄생' KSPO DOME 4저녁(11/23·24·30, 12/1, 18:00 시작, 적힌 130분)의 9호선 올림픽공원·한성백제 1시간 승차.
  바닥: 같은 요일·큰 공연 없는 2024 날 중 가까운 6일(작년 11~12월 근처엔 없어서 4~8월 날이 쓰임 — 인원보다 시간대 몫을 봐요).
방법: 2025에서 정한 연결(주차 출차 시작 → 역 승차 걷는 시간 0분, 사람 모양 = 출차 모양 0.5배)로, 저녁마다 '출차 시작 − 적힌 종료'(L)를 −40~+80분에서 골라
  역 시간대 몫(TV)이 가장 맞는 값을 찾아요. 퇴장 시작 확률 = 80% × (네 L을 10분 커널로) + 20% × P0(2025 전체, 너무 자신하지 않게).
사용: data 폴더에서 python3 ../analysis/exitprob_artist.py"""
import os, sys, io, json, contextlib, numpy as np, pandas as pd
sys.argv = ['x', 'schedule']; __file__ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0] if False else __file__)), 'station_split_2024.py'))
src = open(__file__, encoding='utf-8').read().split("if MODE == 'schedule': sys.exit(0)")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
def base_any(s, d, h):
    t = pd.Timestamp(d); c = sorted((abs((pd.Timestamp(x) - t).days), x) for x in NOS[t.weekday()])[:6]; return float(np.median([ON9[s][x].get(h, 0) for _, x in c]))
K_SCALE = 1335 / 2056  # exitprob_prereg_20261127.json과 같은 2026 단위
J = S[S.seq.str.contains('조용필')].reset_index(drop=True)
shape = np.median(np.vstack(EVN['shape'].values), axis=0); shape /= shape.sum(); shape = squeeze(shape, 0.5)
LS = np.arange(-40, 85, 5); fits = []
for r in J.itertuples():
    H = list(range(int(r.st) // 60 + 1, 25)); a = share(sum(np.array([ON9[s][r.d].get(h, 0) - base_any(s, r.d, h) for h in H]) for s in S9))
    err = [tv(pred_share(kde([r.st % 1440 * 0 + 130 + L], bw=0.1), r.st, shape, 0, H), a) for L in LS]
    fits.append(dict(d=r.d, L=int(LS[int(np.argmin(err))]), tv=float(min(err)), tv_at42=float(err[list(LS).index(40)])))
F = pd.DataFrame(fits); print(F.to_string(index=False))
p_art = 0.8 * kde(130 + F.L.values, bw=10) + 0.2 * kde(EVN.onset.values, bw=10); p_art /= p_art.sum()
print('작년 조용필: 출차 시작 − 적힌 종료 L = %s (중앙 %+d분) | 2025 전체는 중앙 %+.0f분' % (list(F.L), int(np.median(F.L)), np.median((EVN.onset - EVN.run).dropna())))
out = dict(what='조용필 작년 기록 반영판(별도, 오늘 아침 고정한 P0·P3는 그대로)', made_at=pd.Timestamp.now(tz='Asia/Seoul').isoformat(timespec='minutes'), fits_2024=fits,
           rule='퇴장 시작 확률 = 0.8×kde(130 + 작년 L, 10분) + 0.2×P0. 나머지(차 모양·크기·바닥·기준·2026 단위)는 exitprob_prereg_20261127.json과 같음',
           scoring='exitprob.py score로 같은 방식 채점(정답 end_detect_live.park_onset). 오늘 아침 P0(첫날)·P3(둘째·셋째 날)와 나란히 비교. 세 저녁뿐이라 방향만 봄', tables={})
for d, t in (('2026-11-27', '19:00'), ('2026-11-28', '18:00'), ('2026-11-29', '17:00')):
    st = hm(t); p, exp, pc, pv, base = forecast(EVN, st, 130, wkg(d), 'P0', pdist=p_art)
    thr26 = {k: v * K_SCALE for k, v in THR.items()}; cs = np.cumsum(p); lo, md, hi = (int(np.searchsorted(cs, q)) for q in (0.1, 0.5, 0.9))
    clock = lambda k: '%02d:%02d' % ((st + 10 * k) // 60 % 24, (st + 10 * k) % 60)
    tab = [dict(slot=clock(k), p_onset=round(float(p[k]), 4), exp_net_2026=round(float(exp[k] * K_SCALE), 1), base_2026=round(float(base[k] * K_SCALE), 1), p_busy=round(float(pc[k]), 4), p_vbusy=round(float(pv[k]), 4)) for k in range(NS)]
    out['tables'][d] = dict(day=d, start=t, runtime=130, how='artist2024', weekday_group=wkg(d), k_scale=K_SCALE, thr_2026=thr26, onset_80=[clock(lo), clock(hi + 1)], onset_median_slot=clock(md), table=tab)
    pk = [x for x in tab if x['p_busy'] >= 0.5]
    print('%s %s 시작: 출차 시작 80%% %s ~ %s, 중앙 %s 칸 | 혼잡 확률 50%% 넘는 칸: %s' % (d, t, clock(lo), clock(hi + 1), clock(md), ', '.join('%s(%.0f%%)' % (x['slot'], 100 * x['p_busy']) for x in pk) or '없음'))
json.dump(out, open('checks/exitprob_artist_20261127.json', 'w'), ensure_ascii=False, indent=1)
