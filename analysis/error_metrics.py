"""오차 지표(2026-11-28): MAE(평균 절대 오차, 예측에서 말하는 MAD와 같은 식), MAPE(평균 절대 백분율 오차),
중앙 절대 오차, 오차의 중앙값 절대 편차(통계에서 말하는 MAD), WAPE(= 100 − 사이트 정확도), 치우침(평균 오차).
예측·정답은 live_recheck.py와 같음: 공연 없는 월~목, 07~23시, 30분 칸(주차)·1시간 칸(인구 2025).
  주차 2025: 하루씩 빼고 같은 요일로 모양을 만든 예상, 정답 = 입출차로 센 주차장 안 차량 수
  주차 2026: 실시간 parking_sum(11/23~26)
  인구 2025: ahead_2025.py(KT 생활인구, 앞선 달로만 배움), 공휴일 낀 날 뺌
실시간 인구(11/22~27, 공연 날 포함)는 analysis/sim/vs_seoul.json에서 따로 셈(맨 아래).
사용: data 폴더에서 python3 ../analysis/error_metrics.py"""
import io, contextlib, json, os, numpy as np, pandas as pd
src = open('../analysis/live_recheck.py', encoding='utf-8').read().split('def boot_mean')[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)


def met(e, y):
    e, y = np.asarray(e, float), np.asarray(y, float); k = ~(np.isnan(e) | np.isnan(y)) & (y > 0); e, y = e[k], y[k]; a = np.abs(e)
    return dict(n=int(len(e)), MAE=a.mean(), MAPE=100 * np.mean(a / y), MdAE=np.median(a),
                MAD=np.median(np.abs(e - np.median(e))), WAPE=100 * a.sum() / y.sum(), bias=e.mean(), ymean=y.mean())


def show(lab, unit, m):
    print('  %-28s n=%5d | MAE %6.0f%s | MAPE %5.1f%% | 중앙 절대 오차 %5.0f%s | 오차 MAD %5.0f%s | WAPE %4.1f%% | 치우침 %+5.0f%s | 평균 정답 %6.0f%s' % (
        lab, m['n'], m['MAE'], unit, m['MAPE'], m['MdAE'], unit, m['MAD'], unit, m['WAPE'], m['bias'], unit, m['ymean'], unit))


out = {}
E = {'dawn': ([], []), 'h2': ([], [])}
for d in wkd:
    oth = [k for k in wkd if k != d and pd.Timestamp(k).weekday() == pd.Timestamp(d).weekday()]
    p = np.median([OCC[k] - NT[k] for k in oth], axis=0) + NT[d]; y = OCC[d]; q = two_h(p, y)
    for k, f in (('dawn', p), ('h2', q)): E[k][0].extend(f[H] - y[H]); E[k][1].extend(y[H])
print('== 주차장 안 차량 수, 2025 지난 기록으로 시험 (공연 없는 월~목 %d일)' % len(wkd))
for k, lab in (('dawn', '새벽 예상'), ('h2', '2시간 앞')): m = met(*E[k]); show(lab, '대', m); out['park_2025_' + k] = m
E = {'dawn': ([], []), 'h2': ([], [])}
for d in ['2026-11-23', '2026-11-24', '2026-11-25', '2026-11-26']:
    ts = pd.to_datetime([f'{d} {t}' for t in slots]); y = pk.reindex(pk.index.union(ts)).interpolate(limit=2).reindex(ts).values
    night = float(pk.reindex(pk.index.union([pd.Timestamp(f'{d} 04:00')])).interpolate().loc[f'{d} 04:00'])
    oth = [k for k in wkd if pd.Timestamp(k).weekday() == pd.Timestamp(d).weekday()]
    p = np.median([OCC[k] - NT[k] for k in oth], axis=0) + night; q = two_h(p, y)
    for k, f in (('dawn', p), ('h2', q)): E[k][0].extend(f[H] - y[H]); E[k][1].extend(y[H])
print('== 주차장 안 차량 수, 2026 실시간 (11/23~26 월~목)')
for k, lab in (('dawn', '새벽 예상'), ('h2', '2시간 앞')): m = met(*E[k]); show(lab, '대', m); out['park_2026_' + k] = m
print('== 공원 인구, 2025 지난 기록으로 시험 (공연 없는 월~목 %d일, KT 생활인구)' % R.d.nunique())
for k, lab in (('none', '새벽 예상'), ('v0', '2시간 앞')): m = met(R[k] - R.y, R.y); show(lab, '명', m); out['pop_2025_' + k] = m
V = json.load(open(next(p for p in ('../analysis/sim/vs_seoul.json', os.path.expanduser('~/bt/vs_seoul.json')) if os.path.exists(p))))
SH = {'2026-11-22': (17, 22), '2026-11-27': (19, 24)}
print('== 공원 인구, 2026 실시간 (11/22~27, 서울시 측정 범위 가운데가 정답, 07~23시 정시)')
for L, lab in ((60, '1시간 30분 앞'), (90, '2시간 앞'), (150, '3시간 앞')):
    A = [r for r in V if r['L'] == L]
    for g, rows in (('전체', A), ('공연 없는 시간', [r for r in A if not (r['d'] in SH and SH[r['d']][0] <= r['h'] <= SH[r['d']][1])]),
                    ('공연 저녁', [r for r in A if r['d'] in SH and SH[r['d']][0] <= r['h'] <= SH[r['d']][1]])):
        for who, key in (('올타임(지금 사이트)', 'main'), ('서울시 공식 예측', 'seoul')):
            m = met([r[key] - r['truth'] for r in rows], [r['truth'] for r in rows]); show(f'{lab} {g} {who}', '명', m); out[f'pop_live_{L}_{g}_{key}'] = m
json.dump(out, open(os.path.expanduser('~/bt/error_metrics.json'), 'w'), ensure_ascii=False, indent=1)
