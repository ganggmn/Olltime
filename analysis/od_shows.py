"""수도권 생활이동 출도착(2025, 일별)으로 KSPO DOME 공연 날 관객이 어디서 와서 어디로 가는지 봐요.
사용: python3 analysis/od_shows.py (analysis/lifemove_od_2025.csv.gz, shows_site_2024-12_2025-12.json)
- 들어옴: 시작 4시간 전~시작 시각에 오륜동에 도착한 이동(출발 자치구·시군별), 나감: 끝난 뒤 2시간 동안 오륜동에서 출발한 이동(도착 자치구·시군별)
- 기준: 같은 요일의 큰 공연 없는 날(그해 안, 가까운 3일) 같은 시각 합의 중앙값. 수단 번호: 4 광역버스, 5 일반버스, 6 지하철, 7 도보, 8 차량, 9 기타"""
import json, numpy as np, pandas as pd
GU = {'11110': '종로구', '11140': '중구', '11170': '용산구', '11200': '성동구', '11215': '광진구', '11230': '동대문구', '11260': '중랑구', '11290': '성북구', '11305': '강북구', '11320': '도봉구', '11350': '노원구', '11380': '은평구', '11410': '서대문구', '11440': '마포구', '11470': '양천구', '11500': '강서구', '11530': '구로구', '11545': '금천구', '11560': '영등포구', '11590': '동작구', '11620': '관악구', '11650': '서초구', '11680': '강남구', '11710': '송파구', '11740': '강동구',
      '41450': '하남시', '41360': '남양주시', '41130': '성남시', '41131': '성남 수정', '41133': '성남 중원', '41135': '성남 분당', '41460': '용인시', '41465': '용인 수지', '41463': '용인 기흥', '41110': '수원시', '41310': '구리시', '41610': '광주시', '41280': '고양시', '41170': '안양시', '41190': '부천시', '41270': '안산시', '41390': '시흥시', '41410': '군포시', '41570': '김포시', '41590': '화성시', '41220': '평택시', '41150': '의정부시', '28': '인천', '41': '경기'}
MODE = {4: '광역버스', 5: '일반버스', 6: '지하철', 7: '도보', 8: '차량', 9: '기타'}
FIX = {'�궡援��씤': '내국인', '�떒湲곗쇅援��씤': '단기외국인', '�옣湲곗쇅援��씤': '장기외국인'}
O = pd.read_csv('analysis/lifemove_od_2025.csv.gz', dtype={'other_gu': str, 'hour': str}); O['h'] = O.hour.astype(int); O['who'] = O.who.replace(FIX)
SH = json.load(open('analysis/shows_site_2024-12_2025-12.json', encoding='utf-8')); dome = {}
for s in SH['list']:
    if s['venue'] == 'KSPO DOME' and s['d'].startswith('2025'): dome.setdefault(s['d'], s)
HOL = {'2025-01-01', '2025-01-27', '2025-01-28', '2025-01-29', '2025-01-30', '2025-03-03', '2025-05-05', '2025-05-06', '2025-06-03', '2025-06-06', '2025-08-15', '2025-10-03', '2025-10-06', '2025-10-07', '2025-10-08', '2025-10-09', '2025-12-25'}
days = sorted(O.date.unique()); base_pool = [d for d in days if d not in dome and d not in HOL]
wd = lambda d: pd.Timestamp(d).weekday()
def agg(side, d, hs, by): q = O[(O.date == d) & (O.side == side) & O.h.isin(hs)]; return q.groupby(by).cnt.sum()
res = {'in': [], 'out': []}; modes = {'in': [], 'out': []}; whos = []; tt = []
for d, s in dome.items():
    if d not in days or d in HOL: continue
    st = int(s['t'][:2]); en = st + int(np.ceil(((s.get('run') or 150) + 15) / 60))
    b = sorted([x for x in base_pool if wd(x) == wd(d)], key=lambda x: abs((pd.Timestamp(x) - pd.Timestamp(d)).days))[:3]
    if len(b) < 2: continue
    for side, hs in (('in', range(st - 4, st + 1)), ('out', range(en, min(en + 2, 24)))):
        for by, store in (('other_gu', res), ('mode', modes)):
            cur = agg(side, d, hs, by); bb = pd.concat([agg(side, x, hs, by) for x in b], axis=1).fillna(0).median(axis=1)
            store[side].append(cur.sub(bb, fill_value=0))
    cur = agg('in', d, range(st - 4, st + 1), 'who'); bb = pd.concat([agg('in', x, range(st - 4, st + 1), 'who') for x in b], axis=1).fillna(0).median(axis=1); whos.append(cur.sub(bb, fill_value=0))
    q = O[(O.date == d) & (O.side == 'in') & O.h.isin(range(st - 4, st + 1))]; tt.append((q.groupby('mode').min_x_cnt.sum() / q.groupby('mode').cnt.sum()))
n = len(res['in']); print('KSPO DOME 공연 날 %d일(같은 요일 큰 공연 없는 날과 견줌)' % n)
for side, lab in (('in', '들어옴(시작 4시간 전~시작)'), ('out', '나감(끝난 뒤 2시간)')):
    M = pd.concat(modes[side], axis=1).fillna(0).median(axis=1); pos = M.clip(lower=0)
    print('\n%s 수단별 증가(중앙값): %s' % (lab, ', '.join('%s %+.0f(%.0f%%)' % (MODE.get(int(k), k), v, 100 * max(v, 0) / pos.sum()) for k, v in M.sort_values(ascending=False).items())))
    Gs = pd.concat(res[side], axis=1).fillna(0); g = Gs.median(axis=1).sort_values(ascending=False); tot = g.clip(lower=0).sum()
    print('%s 지역별 증가 상위(중앙값, 몫): %s' % (lab, ', '.join('%s %+.0f(%.0f%%)' % (GU.get(k, GU.get(k[:2], k)), v, 100 * v / tot) for k, v in g.head(12).items())))
    seoul = g[g.index.str.startswith('11')].clip(lower=0).sum(); print('   서울 %.0f%%, 서울 밖 %.0f%%' % (100 * seoul / tot, 100 * (tot - seoul) / tot))
W_ = pd.concat(whos, axis=1).fillna(0).median(axis=1); print('\n들어온 사람 중 내·외국인(증가 중앙값): %s' % W_.round().to_dict())
T_ = pd.concat(tt, axis=1).median(axis=1); print('공연 날 들어온 이동의 평균 걸린 시간(분, 중앙값): %s' % {MODE.get(int(k), k): round(v) for k, v in T_.items()})
