"""출차 혼잡 '시작' 실시간 알림 규칙 비교(2025 KSPO DOME 단독 저녁, 입출차 기록 5분).
지금 M8: 주차 10분 6.5% 감소(end_detect)가 울린 시각 + 2025 중앙값 간격.
새 후보: 10분 순유출(나간 차 − 들어온 차)이 θ대 이상인 읽기가 n번 연속이면 울림(가장 이른 때 E 이후).
고르기: 1~6월 저녁(놓침 + 혼잡 시작 20분 넘게 앞선 울림 + 혼잡 없는 저녁 울림 ≤ 5%) 중 구간 겹침 평균이 가장 큰 규칙. 채점: 7·10·11월.
간격(울림 → 혼잡 시작·최대·끝)은 학습 저녁에서 같은 투어를 뺀 중앙값."""
import os, sys, json, pickle, calendar, numpy as np, pandas as pd
D = sys.argv[1]; os.chdir(D)
P = pickle.load(open(os.path.expanduser('~/past3.pkl'), 'rb')); SHOW = P['show']
hm = lambda t: int(t[:2]) * 60 + int(t[3:5])
E = json.load(open('checks/end_detect_2025.json')); EV = E['1~6월(정할 때 쓴 저녁)']['evenings'] + E['7·10·11월(채점)']['evenings']
df = pd.read_csv('inout_2025_full.csv', usecols=['entry_gate', 'entry_time', 'exit_time'], encoding='utf-8-sig'); df = df[~df.entry_gate.str.contains('CMB')]
en = pd.to_datetime(df.entry_time, errors='coerce').dropna(); ex = pd.to_datetime(df.exit_time, errors='coerce').dropna()
B5 = lambda s: s.dt.floor('5min').value_counts()
NET = (B5(ex).sub(B5(en), fill_value=0)).sort_index()
bad = lambda d: d[5:7] in ('08', '09') or (d[5:7] == '11' and int(d[8:]) > 6) or (d[5:7] == '12' and int(d[8:]) > 7) or int(d[8:]) == calendar.monthrange(int(d[:4]), int(d[5:7]))[1]
dome = lambda d: [b for b in SHOW.get(d, {}).get('big', []) if 'KSPO' in b['venue']]
THR = 120.0; I0 = 6
ROWS = []
for e in EV:
    d = e['d']; b = dome(d)
    if len(b) != 1 or bad(d): continue
    st = hm(b[0]['t']); run = b[0].get('run'); run = float(run) if run == run and run is not None else np.nan
    idx = pd.date_range(pd.Timestamp(d) + pd.Timedelta(minutes=st), periods=72, freq='5min'); n5 = NET.reindex(idx).fillna(0).values
    s = n5.reshape(-1, 2).sum(1); busy = [i for i in range(I0, 36) if s[i] >= THR]
    ROWS.append(dict(d=d, tour=b[0]['short'], st=st, run=run, sched=run if run == run else 150.0, n5=n5, fire0=float(e['fire']) if e['fire'] is not None else None,
                     bs=busy[0] * 10 if busy else None, be=busy[-1] * 10 if busy else None, pk=int(I0 + np.argmax(s[I0:])) * 10, hasbusy=bool(busy), m=int(d[5:7])))
R = pd.DataFrame(ROWS)
def fire_rule(r, th, n, ew):
    e0 = {'E0': 60, 'E1': max(60, r.sched - 45), 'E2': max(60, r.sched - 60)}[ew]
    run_ = 0
    for k in range(2, 73):
        t = 5 * k; r10 = r.n5[k - 2] + r.n5[k - 1]
        if t < e0: continue
        run_ = run_ + 1 if r10 >= th else 0
        if run_ >= n: return float(t)
    return None
def score(T, Q, col):
    """T: 학습, Q: 채점. col: 울림 시각 열. 반환 요약."""
    out = dict(bs=[], pk=[], be=[], iou=[], lead=[], false=0, miss=0, n=len(Q))
    for _, q in Q.iterrows():
        f = q[col]
        if f is None or f != f:
            out['miss'] += int(q.hasbusy); continue
        if not q.hasbusy: out['false'] += 1; continue
        if f < q.bs - 20: out['false'] += 1
        Tt = T[(T.tour != q.tour) & T[col].notna()]; TB = Tt[Tt.hasbusy]
        o = (float(np.median(TB.bs - TB[col])), float(np.median(Tt.pk - Tt[col])), float(np.median(TB.be - TB[col])))
        bs, pk, be = f + o[0], f + o[1], f + o[2]
        out['bs'].append(bs - q.bs); out['pk'].append(pk - q.pk); out['be'].append(be - q.be); out['lead'].append(f - q.bs)
        a0, a1, b0, b1 = bs, be + 10, q.bs, q.be + 10; inter = max(0, min(a1, b1) - max(a0, b0)); uni = max(a1, b1) - min(a0, b0); out['iou'].append(inter / uni if uni > 0 else 0)
    A = lambda v: np.abs(np.array(v))
    return dict(n=out['n'], false=out['false'], miss=out['miss'], bad_rate=round((out['false'] + out['miss']) / out['n'], 3),
                fire_minus_bs_med=float(np.median(out['lead'])) if out['lead'] else None,
                fire_minus_bs_p10_p90=[float(np.percentile(out['lead'], 10)), float(np.percentile(out['lead'], 90))] if out['lead'] else None,
                bs_abs_med=float(np.median(A(out['bs']))), bs_hit20=round(float(np.mean(A(out['bs']) <= 20)) * 100), pk_abs_med=float(np.median(A(out['pk']))), pk_hit20=round(float(np.mean(A(out['pk']) <= 20)) * 100),
                be_abs_med=float(np.median(A(out['be']))), be_hit20=round(float(np.mean(A(out['be']) <= 20)) * 100), iou=round(float(np.mean(out['iou'])), 3))
rules = [('M8 지금(6.5%)', None, None, None)] + [(f'θ{th} n{n} {ew}', th, n, ew) for th in (60, 80, 100, 120, 150, 180) for n in (1, 2) for ew in ('E0', 'E1', 'E2')]
for name, th, n, ew in rules:
    R[name] = R['fire0'] if th is None else [fire_rule(r, th, n, ew) for _, r in R.iterrows()]
TR = R[R.m <= 6]; TE = R[R.m >= 7]
res = {}
for name, *_ in rules:
    res[name] = dict(train=score(TR, TR, name), test=score(TR, TE, name), all_loto=score(R, R, name))
ok = [k for k in res if res[k]['train']['bad_rate'] <= 0.05 and k != 'M8 지금(6.5%)']
best = max(ok, key=lambda k: (res[k]['train']['iou'], -res[k]['train']['bs_abs_med'])) if ok else None
# 울림 → 혼잡 시작·최대·끝 간격(2025 전체, 2026 적용용)
def offs(col):
    T = R[R[col].notna()]; TB = T[T.hasbusy]
    return dict(bs=float(np.median(TB.bs - TB[col])), pk=float(np.median(T.pk - T[col])), be=float(np.median(TB.be - TB[col])))
json.dump(dict(n=len(R), n_tr=len(TR), n_te=len(TE), tours=int(R.tour.nunique()), best=best, best_offsets=offs(best) if best else None, m8_offsets=offs('M8 지금(6.5%)'), res=res), open(os.path.expanduser('~/bt/exit_alarm_out.json'), 'w'), ensure_ascii=False, indent=1)
print('저녁', len(R), '학습', len(TR), '채점', len(TE), '고른 규칙', best)
for k in ['M8 지금(6.5%)'] + sorted(ok, key=lambda k: -res[k]['train']['iou'])[:8]:
    a, b = res[k]['train'], res[k]['test']
    print('%-16s 학습 겹침 %.2f 나쁨 %.0f%% 시작오차 %.0f | 채점 겹침 %.2f 나쁨 %d/%d 울림-시작 %+.0f [%+.0f,%+.0f] 시작 %.0f(%d%%) 최대 %.0f(%d%%) 끝 %.0f(%d%%)' % (
        k, a['iou'], 100 * a['bad_rate'], a['bs_abs_med'], b['iou'], b['false'] + b['miss'], b['n'], b['fire_minus_bs_med'], *b['fire_minus_bs_p10_p90'], b['bs_abs_med'], b['bs_hit20'], b['pk_abs_med'], b['pk_hit20'], b['be_abs_med'], b['be_hit20']))
