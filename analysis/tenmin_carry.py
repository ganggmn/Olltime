"""'H 같은 공연 전날 보정': 11/27(금, 19시 시작) 조용필 실시간 10분 곡선과 고정해 둔 11/27 예측(tenmin_forecasts_20261126.json)의
모델별 오차(실제 증가 − 예측 증가, 그날 새벽 기준)를 공연 시작 기준으로 맞춰, 11/28(토, 18시 시작) 같은 모델 예측에 0.8배 더함.
- 시작 시각 차이 −1시간만큼 옮김(10분 칸 −6). 더하는 범위: 시작 기준 −6시간 ~ +6시간(showmodel.py carry와 같은 창).
- 비어 있는 10분 칸의 오차는 앞뒤를 이어 채움(창 안에서만).
- 근거: showmodel.py 2025 결과(둘째 날 이후 큰 공연 81 → 89%).
사용: data 폴더에서 python3 ../analysis/tenmin_carry.py → checks/tenmin_forecasts_20261128_carry.json"""
import sys, os, json, numpy as np, pandas as pd, datetime as dt
sys.argv = ['tenmin.py', 'none']; exec(open(os.path.join('..', 'analysis', 'tenmin.py'), encoding='utf-8').read())
F = json.load(open('checks/tenmin_forecasts_20261126.json', encoding='utf-8'))
P, D, ALPHA = '2026-11-27', '2026-11-28', 0.8
vp, vd = F['days'][P], F['days'][D]
cp = curve(RT, P); dawn = dawn_of(RT, P); act = cp - dawn
sp, sd = int(round(vp['start'] * 6)), int(round(vd['start'] * 6)); sh = sd - sp
out = {'made_at': dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec='minutes'),
       'note': "11/28 'H 같은 공연 전날 보정' 모델. 각 값은 그날 새벽 값(anchor)에 더할 10분별 증가(명). 원래 모델 + 0.8 × 11/27 오차(시작 기준으로 −6칸 옮김, 시작 −6시간~+6시간만)",
       'from': {'forecasts': 'analysis/tenmin_forecasts_20261126.json (sha256 146bbfac1f12048b)', 'prev_day': P, 'prev_dawn': round(float(dawn)), 'alpha': ALPHA, 'shift_10min': sh, 'window_rel_h': [-6, 6]},
       'days': {D: {k: vd[k] for k in vd if k != 'models'}}}
out['days'][D]['models'] = {}; dbg = {}
for name, inc in vp['models'].items():
    r = act - np.array(inc, float)
    win = np.arange(max(0, sp - 36), min(NB, sp + 36)); rr = pd.Series(r[win]).interpolate(limit_direction='both').values
    m = np.array(vd['models'][name], float).copy()
    for j, k in enumerate(win):
        t = k + sh
        if 0 <= t < NB: m[t] += ALPHA * rr[j]
    out['days'][D]['models'][name + ' +H 전날 보정'] = [round(float(x)) for x in m]
    dbg[name] = (round(float(np.nanmean(np.abs(r[win])))), round(float(np.nanmean(r[win]))))
json.dump(out, open('checks/tenmin_forecasts_20261128_carry.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('11/27 새벽', round(dawn), '| 모델별 11/27 시작±6시간 평균 |오차|, 평균 오차(실제−예측):', dbg)
a = vd['anchor']
for nm, mm in out['days'][D]['models'].items(): print('  %-40s 18:00 %6d  20:00 %6d  21:00 %6d  22:00 %6d' % (nm, a + mm[108], a + mm[120], a + mm[126], a + mm[132]))
