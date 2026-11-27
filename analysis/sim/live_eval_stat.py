"""live_eval.json·exit_eve.json 채점(2026-11-28): 사람 수 세 방식 비교와 신뢰구간, 혼잡 경보 정밀도·재현율.
- 사람 수(11/22~27, 07~23시 정시): 올타임(지금 사이트) vs 서울시 공식 예측 vs 현재값 유지. 날 단위 재표집 4,000번(6일이라 구간이 넓음).
- 사람 수 경보(5분마다, 2시간 앞): 서울시 단계가 '약간 붐빔 이상' / '붐빔'인 때를 맞히는지. 올타임은 사람 수 문턱
  (서울시 범위에서 '약간 붐빔'이 나온 가장 낮은 값 10,000명, '붐빔' 14,000명 — 채점 전에 정함), 현재값 유지는 2시간 전 단계.
  정시 97개에서는 서울시 공식 예측 단계도 같이 봄.
- 주차 경보(20분마다, 2시간 앞, 11/23~27): 사이트 주차 칸 기준(2,200대의 70% '약간 혼잡' 1,540대, 90% '만차' 1,980대).
- 출차 혼잡 시작 알림(2025 88저녁·2024 7월 7저녁, 지금 규칙 N2와 예전 규칙): 맞힘 = 혼잡 시작 ±20분 안에 울림.
  정밀도 = 맞힘 ÷ 울린 저녁, 재현율 = 맞힘 ÷ 혼잡 있던 저녁.
사용: python3 live_eval_stat.py (같은 폴더의 live_eval.json, exit_eve.json)"""
import json, os, numpy as np
D = os.path.dirname(os.path.abspath(__file__)); J = json.load(open(os.path.join(D, 'live_eval.json'))); X = json.load(open(os.path.join(D, 'exit_eve.json')))
rng = np.random.default_rng(20261128); OUT = {}
SH = {'2026-11-22': (17, 22), '2026-11-27': (19, 24)}
def mae(rs, k): return float(np.mean([abs(r[k] - r['truth']) for r in rs]))
print('== 사람 수: 같은 조건 비교(정답 = 서울시 측정 범위 가운데)')
for L, lab in ((60, '1시간 30분 앞'), (90, "2시간 앞(사이트 '2시간 앞'과 같은 조건)"), (150, '3시간 앞')):
    A = [r for r in J['ppl'] if r['L'] == L]
    for g, rs in (('전체', A), ('공연 저녁', [r for r in A if r['d'] in SH and SH[r['d']][0] <= r['h'] <= SH[r['d']][1]])):
        days = sorted({r['d'] for r in rs}); by = {d: [r for r in rs if r['d'] == d] for d in days}; B = []
        for _ in range(4000):
            S = [r for i in rng.integers(0, len(days), len(days)) for r in by[days[i]]]; B.append([mae(S, 'main') - mae(S, 'seoul'), mae(S, 'main') - mae(S, 'pers')])
        B = np.array(B); q = lambda c: [float(np.percentile(B[:, c], p)) for p in (2.5, 97.5, .5, 99.5)]
        r = dict(n=len(rs), days=len(days), main=mae(rs, 'main'), seoul=mae(rs, 'seoul'), pers=mae(rs, 'pers'), main_minus_seoul=q(0), main_minus_pers=q(1),
                 mape_main=100 * float(np.mean([abs(x['main'] - x['truth']) / x['truth'] for x in rs])), mape_seoul=100 * float(np.mean([abs(x['seoul'] - x['truth']) / x['truth'] for x in rs])), mape_pers=100 * float(np.mean([abs(x['pers'] - x['truth']) / x['truth'] for x in rs])))
        OUT[f'ppl_L{L}_{g}'] = r
        print('  %s %s n=%d(%d일) | MAE 올타임 %.0f · 서울시 %.0f · 현재값 유지 %.0f명 | MAPE %.1f%% · %.1f%% · %.1f%% | 올타임−서울시 %+.0f(95%% %+.0f~%+.0f) | 올타임−유지 %+.0f(95%% %+.0f~%+.0f, 99%% %+.0f~%+.0f)' % (
            lab, g, r['n'], r['days'], r['main'], r['seoul'], r['pers'], r['mape_main'], r['mape_seoul'], r['mape_pers'], r['main'] - r['seoul'], *r['main_minus_seoul'][:2], r['main'] - r['pers'], *r['main_minus_pers']))
def pr(alarm, event):
    a, e = np.array(alarm, bool), np.array(event, bool); tp = int((a & e).sum()); fp = int((a & ~e).sum()); fn = int((~a & e).sum())
    return dict(tp=tp, fp=fp, fn=fn, alarms=int(a.sum()), events=int(e.sum()), precision=tp / a.sum() if a.sum() else None, recall=tp / e.sum() if e.sum() else None)
def show_pr(lab, r):
    f = lambda v: '-' if v is None else '%.0f%%' % (100 * v)
    print('  %-44s 정밀도 %s(%d/%d) · 재현율 %s(%d/%d)' % (lab, f(r['precision']), r['tp'], r['alarms'], f(r['recall']), r['tp'], r['events']))
LVN = {'여유': 0, '보통': 1, '약간 붐빔': 2, '붐빔': 3}; TH = {2: 10000, 3: 14000}
print('== 사람 수 혼잡 경보(2시간 앞, 5분마다 07~23시, 11/22~27, n=%d)' % len(J['ppl5']))
for k, nmk in ((2, "'약간 붐빔' 이상"), (3, "'붐빔'")):
    ev = [LVN[r['lvl']] >= k for r in J['ppl5']]
    for who, al in (('올타임(%s명 넘으면)' % format(TH[k], ','), [r['main'] >= TH[k] for r in J['ppl5']]), ('현재값 유지(2시간 전 단계)', [LVN.get(r['persLvl'], 0) >= k for r in J['ppl5']])):
        r = pr(al, ev); OUT[f'ppl5_{k}_{who[:3]}'] = r; show_pr(f'{nmk} {who}', r)
H = [r for r in J['ppl'] if r['L'] == 90]
print('== 같은 경보, 정시 97개(서울시 공식 예측 단계도 같이)')
for k, nmk in ((2, "'약간 붐빔' 이상"), (3, "'붐빔'")):
    ev = [LVN[r['lvl']] >= k for r in H]
    for who, al in (('올타임', [r['main'] >= TH[k] for r in H]), ('서울시 공식 예측 단계', [LVN.get(r['seoulLvl'], 0) >= k for r in H]), ('현재값 유지', [r['pers'] >= TH[k] for r in H])):
        r = pr(al, ev); OUT[f'pplH_{k}_{who[:3]}'] = r; show_pr(f'{nmk} {who}', r)
C = J['car']; print('== 주차 경보(2시간 앞, 20분마다 07~23시, 11/23~27 n=%d, 큰 공연 날은 11/27 하루)' % len(C))
for th, nmk in ((1540, "'약간 혼잡' 이상(1,540대)"), (1980, "'만차'(1,980대)")):
    ev = [r['truth'] >= th for r in C]
    for who, k in (('사이트 2시간 앞', 'main'), ('현재값 유지', 'pers')):
        r = pr([x[k] >= th for x in C], ev); OUT[f'car_{th}_{k}'] = r; show_pr(f'{nmk} {who}', r)
print('== 출차 혼잡 시작 알림(맞힘 = 혼잡 시작 ±20분 안에 울림)')
for yr in ('2025', '2024'):
    E = X[yr]
    for rule, k in (('지금 규칙(N2, 11/28부터)', 'alarm_new'), ('예전 규칙(11/27까지)', 'alarm_old')):
        tp = sum(1 for e in E if e[k] is not None and e['bs'] is not None and abs(e[k] - e['bs']) <= 20)
        al = sum(1 for e in E if e[k] is not None); ev = sum(1 for e in E if e['bs'] is not None)
        none_ok = sum(1 for e in E if e[k] is None and e['bs'] is None); none = sum(1 for e in E if e['bs'] is None)
        r = dict(tp=tp, alarms=al, events=ev, precision=tp / al if al else None, recall=tp / ev if ev else None, quiet_ok=none_ok, quiet=none, n=len(E)); OUT[f'exit_{yr}_{k}'] = r
        print('  %s %s %d저녁 | 정밀도 %.0f%%(%d/%d) · 재현율 %.0f%%(%d/%d) | 혼잡 없던 저녁 %d개 중 안 울림 %d' % (yr, rule, len(E), 100 * r['precision'], tp, al, 100 * r['recall'], tp, ev, none, none_ok))
json.dump(OUT, open(os.path.join(D, 'live_eval_stat.json'), 'w'), ensure_ascii=False, indent=1)
