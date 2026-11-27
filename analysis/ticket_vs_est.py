"""실제 숫자(티켓 판매 매수)와 추정 인원의 비교(2026-11-28). 현장에서 사람을 셀 수는 없어서, 공연마다 실제로 센 값인
KOPIS 판매 매수(출처: 공연예술통합전산망 KOPIS)를 '그날 공연에 온 사람'의 기준으로 삼고, 기지국 기반 추정(KT 생활인구 → 서울시 '올림픽공원' 영역)으로 본
공연 중 늘어난 인원(공연 중 − 같은 요일·앞뒤 4주 공연 없는 날)과 견줌. 자료: checks/during_show_level_2025.csv(during_show_level.py).
- 평일만 깨끗함(주말·공휴일은 공연 없는 날도 축제·행사로 크게 흔들림). 평일·주말 따로.
- 공연 단위 신뢰구간: 같은 공연(이름) 묶음을 통째로 다시 뽑는 재표집 4,000번.
사용: data 폴더에서 python3 ../analysis/ticket_vs_est.py"""
import json, os, numpy as np, pandas as pd
T = pd.read_csv('checks/during_show_level_2025.csv'); T = T[T.tickets.notna() & (T.tickets > 0)]
rng = np.random.default_rng(20261128); out = {}
for grp in ('평일', '주말·공휴일'):
    S = T[T.grp == grp].copy(); S['r'] = S.excess / S.tickets; S['ape'] = (S.excess - S.tickets).abs() / S.tickets
    G = {k: v for k, v in S.groupby('name')}; names = list(G); B = []
    for _ in range(4000):
        Z = pd.concat([G[names[i]] for i in rng.integers(0, len(names), len(names))])
        B.append([Z.r.median(), np.corrcoef(Z.tickets, Z.excess)[0, 1] if Z.tickets.nunique() > 1 else np.nan, Z.ape.mean()])
    B = np.array(B); q = lambda c: [float(np.nanpercentile(B[:, c], 2.5)), float(np.nanpercentile(B[:, c], 97.5))]
    r = dict(days=len(S), shows=len(names), tickets_med=float(S.tickets.median()), excess_med=float(S.excess.median()), per_ticket_med=float(S.r.median()), per_ticket_ci95=q(0),
             per_ticket_p10_p90=[float(S.r.quantile(.1)), float(S.r.quantile(.9))], corr=float(np.corrcoef(S.tickets, S.excess)[0, 1]), corr_ci95=q(1), mape_vs_tickets=100 * float(S.ape.mean()), mape_ci95=[100 * v for v in q(2)])
    out[grp] = r
    print('%s %d일(공연 %d개) | 판매 매수 중앙 %.0f매 · 추정 증가 중앙 %.0f명 | 1매당 %.2f명(95%% %.2f~%.2f, 날마다 10~90%% %.2f~%.2f) | 상관 %.2f(95%% %.2f~%.2f) | 추정 증가와 판매 매수 차이 평균 %.0f%%(95%% %.0f~%.0f)' % (
        grp, r['days'], r['shows'], r['tickets_med'], r['excess_med'], r['per_ticket_med'], *r['per_ticket_ci95'], *r['per_ticket_p10_p90'], r['corr'], *r['corr_ci95'], r['mape_vs_tickets'], *r['mape_ci95']))
json.dump(out, open('../analysis/ticket_vs_est_2025.json', 'w'), ensure_ascii=False, indent=1)
