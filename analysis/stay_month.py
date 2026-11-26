"""서울 체류인구(250m, KT) 2025년 11월로 '관객이 언제 오나(도착 모양)'와 '2시간 앞 예측 오차'의 관계를 봐요(탐색).
자료: 서울 열린데이터광장 OA-22892 [내국인] 서울 체류인구(250m) 202511. 출처: 서울특별시·KT, 서울시 통신데이터. 원본은 맥에만 둠(재배포 금지).
준비: data/livingpop/stay/stay_202511_park.csv (월 파일에서 공원 칸만 뽑은 것, 아래 extract 참고)
도착 모양(KSPO DOME 칸, 3시간 넘게 머문 사람 = 체류 코드 180·240, 공연 날 − 같은 요일 무리 공연 없는 날 중앙값):
  late = 시작 직전 1시간(시작 시각의 정각 앞 1시간)에 온 몫, early = 시작 3시간 이전에 온 몫(시작 6시간 전부터 셈)
예측 오차: ahead_showday_why.py와 같은 방식(10월까지로 배운 모양 + 2시간 전 실측 보정)의 11월 공연 날, '시작 3시간 전' 구간.
사용: data 폴더에서 python3 ../analysis/stay_month.py → checks/stay_month.json"""
import os, io, sys, json, runpy, contextlib, pickle, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
P = pickle.load(open(os.path.expanduser('~/past3.pkl'), 'rb')); SHOW = P['show']
HOL = {r[:4] + '-' + r[4:6] + '-' + r[6:] for r in pd.read_csv('holidays.csv', dtype=str).iloc[:, 0]}
cols = ['d', 'dong', 'cell', 'x', 'y', 'h', 'code', 'n'] + ['M%d' % a for a in range(0, 80, 10)] + ['F%d' % a for a in range(0, 80, 10)]
D = pd.read_csv('livingpop/stay/stay_202511_park.csv', encoding='cp949', dtype=str, header=None).iloc[:, :24]; D.columns = cols  # 2025 월 파일은 줄 끝에 빈 칸 4개가 더 있음
D = D[D.d.str.fullmatch(r'\d{8}')]
D['cell'] = D.cell.str[-8:]; D['d'] = D.d.str[:4] + '-' + D.d.str[4:6] + '-' + D.d.str[6:8]
for c in ['n'] + cols[8:]: D[c] = pd.to_numeric(D[c].str.replace(',', ''), errors='coerce').fillna(0)
D['h'] = D.h.astype(int); D['code'] = D.code.astype(int)
DOME = '67004650'
L = D[(D.cell == DOME) & (D.code >= 180)].groupby(['d', 'h']).n.sum().unstack().reindex(columns=range(24)).fillna(0)
days = sorted(L.index)
def dome(d): return [b for b in SHOW.get(d, {}).get('big', []) if 'KSPO' in b['venue']]
grp = lambda d: '주말·공휴일' if pd.Timestamp(d).weekday() >= 5 or d in HOL else ('금' if pd.Timestamp(d).weekday() == 4 else '월~목')
noshow = [d for d in days if not dome(d)]
print('11월 날 %d일, KSPO DOME 공연 없는 날 %d일: %s' % (len(days), len(noshow), {g: sum(grp(d) == g for d in noshow) for g in ['월~목', '금', '주말·공휴일']}))
BASE = L.loc[noshow].median()  # 공연 없는 날 전체 중앙(주말 공연 없는 날이 없어서 하나로 씀)
print('공연 없는 날 DOME 칸 3시간+ 도착(시각별 중앙):', BASE.loc[10:20].round(0).astype(int).to_dict())
AU = pd.read_csv('checks/audience_demo_2025.csv'); AU = AU.set_index('d')
rows = []
for d in days:
    b = dome(d)
    if len(b) != 1: continue
    hh, mm = map(int, b[0]['t'].split(':')); sh = hh  # 시작 시각의 정각
    A = (L.loc[d] - BASE).clip(lower=0)
    win = A.loc[max(0, sh - 6):sh]; tot = win.sum()
    if tot <= 0: continue
    rows.append(dict(d=d, name=b[0]['short'], start=b[0]['t'], grp=grp(d), long_tot=float(tot),
                     late=float(A.loc[sh - 1] / tot), early=float(A.loc[max(0, sh - 6):sh - 3].sum() / tot), at_start=float(A.loc[sh] / tot),
                     female=AU.female.get(d, np.nan), young=float(AU.a10.get(d, np.nan) + AU.a20.get(d, np.nan) + AU.a30.get(d, np.nan)) if d in AU.index else np.nan))
S = pd.DataFrame(rows)
# 2시간 앞 예측 오차(11월 공연 날, 시작 3시간 전)
with contextlib.redirect_stdout(io.StringIO()): g = runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ahead_showday_why.py'), run_name='x')
N = g['run_month'](11)
E = N[N.ph == '2 시작 3시간 전'].groupby('d').apply(lambda x: pd.Series(dict(err_v0=float((x.y - x.v0).sum() / x.y.sum() * 100), abs_v0=float((x.y - x.v0).abs().sum() / x.y.sum() * 100),
                                                                       err_shape=float((x.y - x.none).sum() / x.y.sum() * 100))), include_groups=False)
S = S.merge(E, left_on='d', right_index=True, how='left')
pd.set_option('display.width', 220)
print(S.round(3).to_string(index=False))
def sp(a, b):
    m = S[[a, b]].dropna(); return m[a].rank().corr(m[b].rank()), len(m)
out = dict(days=S.round(4).to_dict('records'), corr={})
rng = np.random.default_rng(0)
print('\n== 관계(공연 날 %d일, 공연 %d개; 같은 공연 날끼리 닮아서 사실상 공연 수가 표본)' % (len(S), S.name.nunique()))
for a, b in [('late', 'err_v0'), ('late', 'abs_v0'), ('early', 'err_shape'), ('late', 'err_shape'), ('young', 'early'), ('female', 'early'), ('young', 'late')]:
    r, n = sp(a, b)
    # 공연 단위로 섞기: 공연 이름을 묶음으로 재표집해 상관의 95% 구간
    names = S.name.unique(); bs = []
    for _ in range(5000):
        pick = rng.choice(names, len(names)); m = pd.concat([S[S.name == k] for k in pick])[[a, b]].dropna()
        if len(m) > 3 and m[a].nunique() > 1 and m[b].nunique() > 1: bs.append(m[a].rank().corr(m[b].rank()))
    ci = (np.percentile(bs, 2.5), np.percentile(bs, 97.5)) if bs else (np.nan, np.nan)
    print('  %-6s ↔ %-9s 순위 상관 %+.2f (n=%d) | 공연 묶음 재표집 95%% 구간 %+.2f ~ %+.2f' % (a, b, r, n, ci[0], ci[1]))
    out['corr']['%s~%s' % (a, b)] = dict(r=float(r), n=int(n), ci95=[float(ci[0]), float(ci[1])])
print('\n== 공연별 평균')
G = S.groupby('name')[['late', 'early', 'err_v0', 'abs_v0', 'err_shape', 'young', 'female']].mean().round(3); print(G.to_string())
out['by_show'] = G.reset_index().to_dict('records')
json.dump(out, open('checks/stay_month.json', 'w'), ensure_ascii=False, indent=1, default=float)
