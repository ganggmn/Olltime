"""입장 확률표(W) 모델 검증. 1시간 값은 그대로 두고, 시간 안쪽을 '공연 시작 기준 입장 모양'으로 나눠요(2026-11-28 갱민 요청).

고정한 규칙(결과를 보기 전에 이 파일을 커밋해 고정):
- 2026 실측 저녁 세 개:
  - 11/22 로이킴 17:00, 11/27 조용필 19:00: 맥 data/citydata/raw_YYYYMMDD.jsonl.gz
  - 11/28 조용필 18:00: data/checks/seoul5_20261128.csv. 사이트가 모은 서울시 값이고, 기준 시각 기준이에요. 맥 원본에 빈 시각이 많아서 이걸 써요.
  - 값은 서울시 범위의 가운데예요. 5분 값을 10분 칸 평균으로 묶고, 빈 5분은 시간으로 보간해요.
- 창: 공연 시작 S 기준 −180~+60분. 10분 칸 24개 = 1시간 칸 4개(S−3, S−2, S−1, S).
  - 매끈하게 잇는 비교 방식(B·C)에는 1시간 칸 6개(S−4~S+1)를 넣어요.
- 저녁별 모양: F = (x − lo) / (hi − lo).
  - lo = −180~−150분 3칸 평균, hi = 0~+60분 6칸 평균이에요.
  - 확률표 g = 학습에 쓴 저녁들의 F 평균을 3칸 이동평균으로 다듬은 것(끝은 끝값 반복).
- W 방식:
  - H_k(1시간 4칸) ≈ b + R·ḡ_k를 최소제곱으로 맞춰요.
  - 10분 값 v = H_k + R·(g − ḡ_k). 1시간 평균은 정확히 그대로예요.
- 비교 방식:
  - A 계단: 1시간 값을 그 시간 내내 같게.
  - B 직선: 1시간 값을 매시 30분에 두고 직선으로 이음.
  - C 평균 보존 매끈: tenmin.py의 mp와 같은 방식.
- 시험 1 (2026, 한 저녁 빼기):
  - 뺀 저녁의 5분 값으로 1시간 평균을 만든 뒤, 나머지 저녁으로 만든 g로 다시 나눠요. 10분 실제와 비교해요.
  - 지표: 24칸 MAE, 가파른 구간(−90~0분 9칸) MAE, 증가 50%에 닿는 시각의 오차.
  - 50% 기준은 실제 곡선의 lo·hi로 정하고, 모든 방식에 같이 써요.
- 시험 2 (2024·2025):
  - 대상: 정시에 시작한 공연 중 S−3→S 증가가 1,000명 이상인 날(행정동 11710566 시간별, checks/prerise_2024_2025.json).
  - 세 저녁 모두로 만든 g로, S−3 칸과 S 칸만 써서 S−2·S−1 칸 값을 예측해요.
  - 비교: 직선(고르게 옴, 1/3·2/3).
  - 지표: 두 칸 평균 절대오차(명), W가 나은 공연 비율.
  - 신뢰구간: 공연 이름 묶음째 다시 뽑기 4,000번(시드 20261128)으로 95% 구간.
사용: data 폴더에서 python3 ../analysis/arrivalw.py → ../analysis/arrivalw_result.json"""
import gzip, json, numpy as np, pandas as pd

EVE = {'2026-11-22': 1020, '2026-11-27': 1140, '2026-11-28': 1080}


def load5(d):
    if d == '2026-11-28':
        t = pd.read_csv('checks/seoul5_20261128.csv')
        return dict(zip(t.stamp_min, (t.lo + t.hi) / 2))
    s = {}
    for line in gzip.open(f'citydata/raw_{d.replace("-", "")}.jsonl.gz', 'rt', encoding='utf-8'):
        try:
            p = json.loads(line)['response']['CITYDATA']['LIVE_PPLTN_STTS'][0]
        except Exception:
            continue
        t = p['PPLTN_TIME']
        if t[:10] != d:
            continue
        s[int(t[11:13]) * 60 + int(t[14:16])] = (float(p['AREA_PPLTN_MIN']) + float(p['AREA_PPLTN_MAX'])) / 2
    return s


def ten(s, S, a, b):
    """S+a ~ S+b 분을 10분 칸 평균으로(5분 빈 곳 보간). 빈 5분 수도 함께 돌려줘요."""
    m = np.arange(S + a, S + b, 5)
    have = np.array([k in s for k in m])
    known = sorted(s)
    v = np.interp(m, known, [s[k] for k in known])
    return v.reshape(-1, 2).mean(1), int((~have).sum())


def lin_blocks(H, n_per=6):
    H = np.asarray(H, float)
    c = np.arange(len(H)) * n_per + (n_per - 1) / 2
    return np.interp(np.arange(len(H) * n_per), c, H)


def mp_blocks(H, it=60, n_per=6):
    H = np.asarray(H, float)
    y = lin_blocks(H, n_per)
    for _ in range(it):
        y = y + np.repeat(H - y.reshape(-1, n_per).mean(1), n_per)
        z = np.r_[y[0], y, y[-1]]
        y = 0.25 * z[:-2] + 0.5 * z[1:-1] + 0.25 * z[2:]
    return y + np.repeat(H - y.reshape(-1, n_per).mean(1), n_per)


def shape(x):
    lo, hi = x[:3].mean(), x[18:].mean()
    return (x - lo) / (hi - lo)


def table(Fs):
    g = np.mean(Fs, axis=0)
    z = np.r_[g[0], g, g[-1]]
    return (z[:-2] + z[1:-1] + z[2:]) / 3


def W(H4, g):
    gb = g.reshape(4, 6).mean(1)
    A = np.c_[np.ones(4), gb]
    b, R = np.linalg.lstsq(A, H4, rcond=None)[0]
    return np.repeat(H4, 6) + R * (g - np.repeat(gb, 6)), float(R)


TAU = np.arange(-180, 60, 10) + 5  # 10분 칸 가운데(분)
cur, miss = {}, {}
for d, S in EVE.items():
    s = load5(d)
    x6, m6 = ten(s, S, -240, 120)  # S−4 ~ S+1, 36칸
    cur[d], miss[d] = x6, m6

# 시험 1
t1 = {}
for d, S in EVE.items():
    x6 = cur[d]
    H6 = x6.reshape(6, 6).mean(1)
    truth = x6[6:30]
    g = table([shape(cur[k][6:30]) for k in EVE if k != d])
    preds = {
        'A': np.repeat(H6[1:5], 6),
        'B': lin_blocks(H6)[6:30],
        'C': mp_blocks(H6)[6:30],
        'W': W(H6[1:5], g)[0],
    }
    lo, hi = truth[:3].mean(), truth[18:].mean()
    lv = lo + 0.5 * (hi - lo)

    def t50(v):
        i = int(np.argmax(v >= lv))
        return int(TAU[i]) if (v >= lv).any() else None

    steep = (TAU >= -90) & (TAU < 0)
    t1[d] = dict(
        start=f'{S // 60}:{S % 60:02d}', missing5=miss[d], truth_t50=t50(truth),
        res={k: dict(mae=float(np.abs(v - truth).mean()),
                     mae_steep=float(np.abs(v - truth)[steep].mean()),
                     t50=t50(v)) for k, v in preds.items()},
        curves={'tau': TAU.tolist(), 'truth': truth.round().tolist(),
                **{k: np.round(v).tolist() for k, v in preds.items()}})

# 시험 2
gall = table([shape(cur[k][6:30]) for k in EVE])
gb = gall.reshape(4, 6).mean(1)
fW = [(gb[1] - gb[0]) / (gb[3] - gb[0]), (gb[2] - gb[0]) / (gb[3] - gb[0])]
o = json.load(open('checks/prerise_2024_2025.json'))
rows = []
for r in o['rows']:
    if 'ppl' not in r:
        continue
    p = r['ppl']
    tot = p['h_0'] - p['h_m3']
    if tot < 1000:
        continue
    obs = [p['h_m2'], p['h_m1']]
    pw = [p['h_m3'] + f * tot for f in fW]
    pl = [p['h_m3'] + f * tot for f in (1 / 3, 2 / 3)]
    rows.append(dict(
        name=r['name'], d=r['d'], tot=tot,
        eW=float(np.mean(np.abs(np.subtract(pw, obs)))),
        eL=float(np.mean(np.abs(np.subtract(pl, obs)))),
        f_obs=[(obs[0] - p['h_m3']) / tot, (obs[1] - p['h_m3']) / tot]))
R2 = pd.DataFrame(rows)
rng = np.random.default_rng(20261128)
names = R2.name.unique()
grp = {n: R2[R2.name == n] for n in names}
bs = []
for _ in range(4000):
    pick = rng.choice(names, len(names))
    B = pd.concat([grp[n] for n in pick])
    bs.append((B.eW.mean(), B.eL.mean(), (B.eL - B.eW).mean()))
bs = np.array(bs)
ci = lambda a: [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]
t2 = dict(
    n=len(R2), n_names=len(names),
    table_fractions=dict(S_minus2=float(fW[0]), S_minus1=float(fW[1])),
    obs_fraction_median=dict(S_minus2=float(np.median([f[0] for f in R2.f_obs])),
                             S_minus1=float(np.median([f[1] for f in R2.f_obs]))),
    obs_fraction_p10_p90=dict(
        S_minus2=[float(np.percentile([f[0] for f in R2.f_obs], q)) for q in (10, 90)],
        S_minus1=[float(np.percentile([f[1] for f in R2.f_obs], q)) for q in (10, 90)]),
    mae_W=float(R2.eW.mean()), mae_lin=float(R2.eL.mean()),
    mae_W_ci=ci(bs[:, 0]), mae_lin_ci=ci(bs[:, 1]),
    diff_lin_minus_W=float((R2.eL - R2.eW).mean()), diff_ci=ci(bs[:, 2]),
    W_better=int((R2.eW < R2.eL).sum()),
    mae_W_rel_tot_median=float(np.median(R2.eW / R2.tot)),
    mae_lin_rel_tot_median=float(np.median(R2.eL / R2.tot)))

out = dict(made='2026-11-28', table_g=np.round(gall, 3).tolist(), tau=TAU.tolist(), test1=t1, test2=t2)
json.dump(out, open('../analysis/arrivalw_result.json', 'w'), ensure_ascii=False, indent=1)

print('확률표 g(세 저녁, 시작 기준 10분 칸 가운데):', dict(zip(TAU.tolist(), np.round(gall, 2).tolist())))
for d, v in t1.items():
    print(d, v['start'], '빈5분', v['missing5'], '실제 50% 도달', v['truth_t50'], '|',
          ' '.join(f"{k}: MAE {r['mae']:.0f} 가파른 {r['mae_steep']:.0f} 50% {r['t50']}" for k, r in v['res'].items()))
for k in 'ABCW':
    print('시험1 평균', k, 'MAE', round(np.mean([t1[d]['res'][k]['mae'] for d in t1])),
          '가파른', round(np.mean([t1[d]['res'][k]['mae_steep'] for d in t1])))
print('시험2', json.dumps(t2, ensure_ascii=False))
