"""구간 혼잡도(공연 탭)의 남쪽·북쪽 방향 사람 수를 기지국(250m 생활인구)으로만 다시 세요. 차 대수에 사람 수를 곱하지 않아요.
사용: data 폴더에서 python3 ../analysis/past3.py 다음에 python3 ../analysis/sec_flow.py (~/past3.pkl)
- 2025년 KSPO DOME 공연 날, 공연 시각에 맞춘 6구간(시작 3~2시간 전 … 끝나고 1~2시간)마다
  테두리 남·북·동·서 칸 인구가 '같은 요일, 앞뒤 8주 안의 KSPO DOME 공연 없는 날(공휴일·명절 뺌)' 같은 시각 중앙값보다 늘어난 만큼의 중앙값.
- 끝난 시각 = 시작 + 공연 시간 + 15분을 올림한 시각."""
import pickle, os, json, numpy as np, pandas as pd
P = pickle.load(open(os.path.expanduser('~/past3.pkl'), 'rb')); ZT, G, show = P['ZT'], P['G'], P['show']
days = sorted(set(ZT.index.get_level_values(0))); TS = {d: pd.Timestamp(d) for d in days}
hol = {d for d, g in G.items() if g.startswith('평일 공휴일') or g == '명절'}
nodome = [d for d in days if 'big' not in show.get(d, {}) and 'fest' not in show.get(d, {}) and d not in hol]
def base(d): return [b for b in nodome if TS[b].weekday() == TS[d].weekday() and 0 < abs((TS[b] - TS[d]).days) <= 56]
Z = ['rim_s', 'rim_n', 'rim_e', 'rim_w', 'park', 'cor_olp']; rows = []
for d in days:
    if 'big' not in show.get(d, {}) or d in hol: continue
    s = min(show[d]['big'], key=lambda x: x['t']); st = int(s['t'][:2]); en = st + int(np.ceil(((s.get('run') or 150) + 15) / 60))
    b = base(d)
    if len(b) < 2 or en + 1 > 23: continue
    hs = [st - 3, st - 2, st - 1, st + 1, en, en + 1]
    r = dict(d=d, wd=TS[d].weekday(), st=st, en=en, nb=len(b))
    for z in Z:
        for i, h in enumerate(hs): r['%s_%d' % (z, i)] = ZT.loc[(d, h), z] - np.median([ZT.loc[(x, h), z] for x in b if (x, h) in ZT.index])
    rows.append(r)
R = pd.DataFrame(rows); R.to_csv('checks/sec_flow_2025.csv', index=False, encoding='utf-8-sig')
print('KSPO DOME 공연 날 %d일(평일 %d, 주말 %d), 기준 날 중앙값 %d일' % (len(R), (R.wd < 5).sum(), (R.wd >= 5).sum(), R.nb.median()))
out = {}
for z in Z:
    v = [int(round(R['%s_%d' % (z, i)].median(), -1)) for i in range(6)]; out[z] = v
    print('%-8s 중앙값 %s  | 25%% %s' % (z, v, [int(round(R['%s_%d' % (z, i)].quantile(.25), -1)) for i in range(6)]))
json.dump(dict(n=len(R), F=out), open('checks/sec_flow_2025.json', 'w'), ensure_ascii=False)
