"""2025년 새 공공데이터를 받아 공원 쪽만 추려 analysis/에 작게 저장해요(GitHub 자동 작업에서 돌려요).
- arr: 수도권 생활이동, 도착 행정동 기준 시간대별 성·연령별 수단(내국인 OA-22655, 외국인 OA-22656), 월별 zip 안에 일별 csv
       → 공원과 맞닿은 행정동만. analysis/lifemove_arr_2025.csv.gz
- fo:  [단기외국인] 행정동별 서울 생활인구(250m, OA-23018), 시간별·국적별 → analysis/forn_temp_2025.csv.gz
- od:  수도권 생활이동 출도착 행정동별 수단(OA-22657, 일별 약 85MB). 공연 날과 비교할 날만.
       오륜동(공원)에 도착한 이동과 오륜동에서 출발한 이동을 출발·도착 자치구, 시각, 수단, 내·외국인으로 묶어 합침 → analysis/lifemove_od_2025.csv.gz
- topis: 서울시 교통량 조사자료(TOPIS 지점별 일자별, 월별 xlsx) → 공원에서 4km 안 지점만. analysis/topis_2025.csv.gz, topis_spots.json
수단 번호: 실제 자료로 확인한 읽기는 4 광역버스, 5 일반버스, 6 지하철, 7 도보, 8 차량, 9 기타(analysis/newdata.py 참고)"""
import csv, gzip, io, json, math, os, sys, urllib.parse, urllib.request, zipfile, collections, datetime
URL = 'https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?useCache=false&infId={inf}&seqNo=&seq={seq}&infSeq={iseq}'
UA = {'User-Agent': 'Mozilla/5.0'}
ORYUN = '11710566'
NEAR = {ORYUN, '11710561', '11710562', '11710520', '11710570', '11710690', '11740640', '11740650', '11740660', '11740690'}
PARK = (37.5195, 127.1225)
def get(inf, seq, tries=3):
    for k in range(tries):
        for iseq in (1, 2, 3):
            try:
                with urllib.request.urlopen(urllib.request.Request(URL.format(inf=inf, seq=seq, iseq=iseq), headers=UA), timeout=900) as r: b = r.read()
                if len(b) > 10000: print(inf, seq, len(b), 'bytes', flush=True); return b
            except Exception as e: print(inf, seq, iseq, 'fail', e, flush=True)
    print('받지 못함', inf, seq, flush=True)
def text(raw):
    for enc in ('utf-8-sig', 'cp949'):
        try: return raw.decode(enc)
        except UnicodeDecodeError: continue
    return raw.decode('utf-8', 'replace')
what = sys.argv[1:] or ['arr', 'fo', 'topis']
if 'arr' in what:
    for inf, who, fn in (('OA-22655', 'in', 'analysis/lifemove_arr_2025.csv.gz'), ('OA-22656', 'forn', 'analysis/lifemove_arr_forn_2025.csv.gz')):
        out = gzip.open(fn, 'wt', encoding='utf-8', newline=''); w = csv.writer(out); head = None; n = 0
        for m in range(1, 13):
            b = get(inf, '2025%02d' % m)
            if not b: continue
            z = zipfile.ZipFile(io.BytesIO(b))
            for name in sorted(z.namelist()):
                if not name.endswith('.csv'): continue
                R = csv.reader(io.StringIO(text(z.read(name)))); h = next(R)
                if head is None: head = h; w.writerow(h)
                elif h != head: print('머리줄 다름', name, h, flush=True); continue
                for r in R:
                    if r and r[0] in NEAR: w.writerow(r); n += 1
        out.close(); print('arr', who, 'rows', n, flush=True)
if 'fo' in what:
    out = gzip.open('analysis/forn_temp_2025.csv.gz', 'wt', encoding='utf-8', newline=''); w = csv.writer(out); head = None; n = 0
    for m in range(1, 13):
        b = get('OA-23018', '2025%02d' % m)
        if not b: continue
        z = zipfile.ZipFile(io.BytesIO(b))
        for name in z.namelist():
            R = csv.reader(io.StringIO(text(z.read(name)))); h = next(R)
            if head is None: head = h; w.writerow(h)
            for r in R:
                if len(r) > 2 and r[2] in NEAR: w.writerow(r); n += 1
    out.close(); print('fo rows', n, flush=True)
if 'od' in what:
    S = json.load(open('analysis/shows_site_2024-12_2025-12.json', encoding='utf-8'))
    dome = sorted({s['d'] for s in S['list'] if s['venue'] == 'KSPO DOME' and s['d'].startswith('2025')})
    others = {s['d'] for s in S['list'] + [x for x in S['small'] if '잔디' in x['venue']] if s['d'].startswith('2025')}  # 큰·중간·작은 공연장과 야외 축제 날만 뺌(아트홀은 거의 매일이라 둠)
    D = lambda s: datetime.date.fromisoformat(s)
    base = set()
    for d in dome:
        for k in (-14, -7, 7, 14):
            x = (D(d) + datetime.timedelta(days=k)).isoformat()
            if x.startswith('2025') and x not in others: base.add(x)
    days = sorted(set(dome) | base); lim = int(os.environ.get('OD_LIMIT', '0') or 0)
    if lim: days = days[:lim]
    print('od days', len(days), '(공연', len(dome), ')', flush=True)
    out = gzip.open('analysis/lifemove_od_2025.csv.gz', 'wt', encoding='utf-8', newline=''); w = csv.writer(out)
    w.writerow(['date', 'side', 'other_gu', 'hour', 'mode', 'who', 'cnt', 'min_x_cnt', 'm_x_cnt']); n = 0
    for d in days:
        b = get('OA-22657', d[2:].replace('-', ''))
        if not b: continue
        z = zipfile.ZipFile(io.BytesIO(b)); A = collections.defaultdict(lambda: [0.0, 0.0, 0.0])
        for name in z.namelist():
            with z.open(name) as f0: first = f0.read(65536)
            try: first.decode('utf-8-sig'); enc = 'utf-8-sig'
            except UnicodeDecodeError as e: enc = 'utf-8-sig' if e.start >= len(first) - 4 else 'cp949'  # 64KB 끝에서 글자가 잘린 경우는 utf-8
            with z.open(name) as f:
                R = csv.reader(io.TextIOWrapper(f, encoding=enc, errors='replace')); h = next(R); ix = {c: i for i, c in enumerate(h)}
                io_, id_, ist, ifn, iwho, imd, idist, itm, icnt = (ix[c] for c in ('o_admdong_cd', 'd_admdong_cd', 'st_time_cd', 'fns_time_cd', 'in_forn_div_nm', 'move_trans', 'move_dist', 'move_time', 'cnt'))
                for r in R:
                    o, dd = r[io_], r[id_]
                    if o != ORYUN and dd != ORYUN: continue
                    try: c = float(r[icnt]); t = float(r[itm]); dist = float(r[idist])
                    except ValueError: continue
                    if dd == ORYUN: k = (d, 'in' if o != ORYUN else 'inside', o[:5], r[ifn], r[imd], r[iwho])
                    else: k = (d, 'out', dd[:5], r[ist], r[imd], r[iwho])
                    a = A[k]; a[0] += c; a[1] += c * t; a[2] += c * dist
        for k, a in A.items(): w.writerow(list(k) + [round(a[0], 2), round(a[1], 1), round(a[2])]); n += 1
        print(d, '묶음', len(A), flush=True)
    out.close(); print('od rows', n, flush=True)
if 'topis' in what:
    import openpyxl
    page = sys.argv[sys.argv.index('topis') + 1] if False else None
    FILES = [('01', '174055413809421952746758349263.xlsx', '4679'), ('02', '174312762918224526237846380719.xlsx', '4759'), ('03', '174529640220426691264729780472.xlsx', '4864'),
             ('04', '174832433748029719200005221983.xlsx', '4966'), ('05', '175092061061432319219278589717.xlsx', '5065'), ('06', '175375276619535151374859764265.xlsx', '5160'),
             ('07', '175878653065540185139319288684.xlsx', '5237'), ('08', '175887002873340268637398193237.xlsx', '5343'), ('09', '176155002493542944887460536194.xlsx', '5414'),
             ('10', '176404305005245437912577385271.xlsx', '5477'), ('11', '176586855817047267166834458966.xlsx', '5517'), ('12', '177147644520552871307730146957.xlsx', '5572')]
    dist = lambda la, lo: math.hypot((la - PARK[0]) * 110900, (lo - PARK[1]) * 88200)
    out = gzip.open('analysis/topis_2025.csv.gz', 'wt', encoding='utf-8', newline=''); w = csv.writer(out); spots = {}; n = 0; head = False
    for mm, path, seq in FILES:
        f = dict(apndFileNm='%s월 서울시 교통량 조사자료(2025).xlsx' % mm, apndFilePathNm=path, bdwrSeq=seq, blbdDivCd='08')
        req = urllib.request.Request('https://topis.seoul.go.kr/downloadFileRefRoom.do', data=urllib.parse.urlencode(f).encode(), headers=dict(UA, Referer='https://topis.seoul.go.kr/refRoom/openRefRoom_2.do'))
        try:
            with urllib.request.urlopen(req, timeout=300) as r: b = r.read()
        except Exception as e: print('topis', mm, 'fail', e, flush=True); continue
        wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True)
        loc = wb[[s for s in wb.sheetnames if '좌표' in s][0]]
        L = list(loc.iter_rows(values_only=True)); H = [str(x or '').replace(' ', '') for x in L[0]]
        c = {k: next(i for i, x in enumerate(H) if k in x) for k in ('지점번호', '지점명', '위도', '경도')}
        for r in L[1:]:
            try: la, lo = float(r[c['위도']]), float(r[c['경도']])
            except (TypeError, ValueError, IndexError): continue
            dm = dist(la, lo)
            if dm <= 4000: spots[r[c['지점번호']]] = dict(name=r[c['지점명']], la=la, lo=lo, m=round(dm), row=[str(x) for x in r])
        ws = wb[[s for s in wb.sheetnames if '년' in s and '월' in s][0]]
        m0 = n; ki = None
        for i, r in enumerate(ws.iter_rows(values_only=True)):
            if ki is None:
                H = [str(x or '').replace(' ', '') for x in r]
                if '지점번호' not in H: continue
                ki = H.index('지점번호'); hcols = [j for j, x in enumerate(H) if x.endswith('시')]; base_cols = [H.index(k) for k in ('일자', '요일', '지점명', '지점번호', '방향', '구분')]
                if not head: w.writerow(['일자', '요일', '지점명', '지점번호', '방향', '구분'] + ['%d시' % k for k in range(24)]); head = True
                continue
            if r and len(r) > ki and r[ki] in spots: w.writerow([r[j] for j in base_cols] + [r[j] if j < len(r) else None for j in hcols]); n += 1
        print('topis', mm, '지점', len(spots), '행', n - m0, '머리줄 위치', ki, flush=True)
    out.close(); json.dump(spots, open('analysis/topis_spots.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1); print('topis rows', n, sorted((v['m'], k, v['name']) for k, v in spots.items()), flush=True)
