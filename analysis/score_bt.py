"""11월 13~23일 '역으로 맞혀 본 예보'(bt.py가 만든 30분 단위 예측)를 실제 주차 대수로 채점해요.
파이썬 표준 라이브러리만 써요. 사용: python3 analysis/score_bt.py

예측 파일 두 개를 같은 실제 값으로 채점해요.
  backtest_20261113_23.json           11월 23일에 만든 원래 파일(bt.py). 공연 날을 11/20~22로 잡았어요.
  backtest_20261113_23_schedule.json  올림픽공원 누리집 일정대로 공연 날을 다시 잡은 파일(bt_schedule.py):
                                      11/13~15 TOMORROW X TOGETHER(KSPO DOME), 11/21~22 로이킴. 11/20은 누리집에 공연이 없어요.
실제 값: actual_parking_20261113_26.csv
  source=logger  다른 대회 참가자가 같은 실시간 주차현황 API를 5분마다 불러 공개한 기록
                 (github.com/wkqhd5095/kspo-parking-logger, parking-data 브랜치 data/parking/날짜.csv, 실패한 호출 행은 뺌). 채점에만 써요.
  source=olltime 올타임 저장소 값(/api/trend), 11/23. 두 기록이 같은 값을 받았는지 맞대 보는 데 써요.
정확도 = 100 × (1 − Σ|예측 − 실제| ÷ Σ실제), 07:00~23:30의 30분 칸. 실제 값은 칸 시각 ±10분 안의 가장 가까운 기록.
'2시간 전 값으로 고침'은 2시간 전 칸의 (실제 − 예측)에 남는 비율(공연 없는 날 0.88, 공연 날 0.85, model.js BETA)을 곱해 더해요.
"""
import csv, json, os, collections
H = os.path.dirname(os.path.abspath(__file__))
act = collections.defaultdict(dict); own = {}
for r in csv.DictReader(open(os.path.join(H, 'actual_parking_20261113_26.csv'), encoding='utf-8')):
    d, t = r['time_kst'].split(' '); m = int(t[:2]) * 60 + int(t[3:])
    if r['source'] == 'logger': act[d].setdefault(m, int(r['parking_sum']))
    else: own[(d, m)] = int(r['parking_sum'])

def at(d, m):
    best = None
    for k, v in act.get(d, {}).items():
        if abs(k - m) <= 10 and (best is None or abs(k - m) < best[0]): best = (abs(k - m), v)
    return None if best is None else best[1]

def score(fn):
    B = json.load(open(os.path.join(H, fn), encoding='utf-8')); slots = [int(s[:2]) * 60 + int(s[3:]) for s in B['slots']]
    out = {}
    for d, x in B['days'].items():
        beta = 0.85 if x['show'] else 0.88
        e0 = e2 = s = 0; n = inb = 0; bias = 0
        for i, m in enumerate(slots):
            if m < 420: continue
            a = at(d, m)
            if a is None: continue
            f = x['mid'][i]; n += 1; s += a; e0 += abs(f - a); bias += f - a; inb += x['low'][i] <= a <= x['high'][i]
            j = slots.index(m - 120) if m - 120 in slots else None; a2 = at(d, m - 120) if j is not None else None
            g = f + beta * (a2 - x['mid'][j]) if a2 is not None else f
            e2 += abs(g - a)
        out[d] = dict(show=x['show'], n=n, sum=s, e0=e0, e2=e2, bias=bias, inb=inb)
    return out

def line(lab, rs):
    n = sum(r['n'] for r in rs); s = sum(r['sum'] for r in rs)
    if not n: return '%-34s 채점할 실제 값 없음' % lab
    e0 = sum(r['e0'] for r in rs); e2 = sum(r['e2'] for r in rs); b = sum(r['bias'] for r in rs)
    return '%-34s %3d칸  정확도 %5.1f%% (평균 %3.0f대, 치우침 %+4.0f대 = %+5.1f%%)  2시간 전 값으로 고침 %5.1f%%  범위 안 %3.0f%%' % (lab, n, 100 * (1 - e0 / s), e0 / n, b / n, 100 * b / s, 100 * (1 - e2 / s), 100 * sum(r['inb'] for r in rs) / n)

W = '월화수목금토일'
import datetime
for fn, lab in (('backtest_20261113_23.json', '원래 파일(공연 날 11/20~22로 잡음)'), ('backtest_20261113_23_schedule.json', '누리집 일정대로(11/13~15, 11/21~22)')):
    R = score(fn); print('\n== ' + lab)
    for d, r in R.items():
        wd = W[datetime.date.fromisoformat(d).weekday()]
        print(line('  %s(%s)%s' % (d[5:], wd, ' 공연' if r['show'] else ''), [r]))
    full = {d: r for d, r in R.items() if r['n'] >= 24}
    print(line('  실제 값이 반나절(24칸) 넘는 날 전체', list(full.values())))
    print(line('  그중 공연 날로 잡은 날', [r for r in full.values() if r['show']]))
    print(line('  그중 공연 없는 날로 잡은 날', [r for r in full.values() if not r['show']]))
    print(line('  공연 없는 월~목', [r for d, r in full.items() if not r['show'] and datetime.date.fromisoformat(d).weekday() < 4]))
    print(line('  공연 없는 날로 잡은 토·일', [r for d, r in full.items() if not r['show'] and datetime.date.fromisoformat(d).weekday() >= 5]))
    print(line('  공연 없는 날로 잡은 금', [r for d, r in full.items() if not r['show'] and datetime.date.fromisoformat(d).weekday() == 4]))

# 두 기록 맞대기: 같은 API를 따로 받은 값이 같은지(11/23, ±2분 안)
pairs = [(v, act['2026-11-23'][k]) for (d, m), v in own.items() for k in act.get(d, {}) if abs(k - m) <= 2]
if pairs:
    diff = [abs(a - b) for a, b in pairs]
    print('\n두 기록 맞대기(11/23): %d쌍, 평균 %.1f대 차이, 가장 큰 차이 %d대' % (len(pairs), sum(diff) / len(diff), max(diff)))
