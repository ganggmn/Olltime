"""2025년 공원 둘레의 버스 정류장 일별 승하차와 따릉이 대여 이력을 서울 열린데이터광장 파일에서 뽑아요(GitHub 자동 작업에서 돌려요).
- 버스: 서울시 버스노선별 정류장별 승하차 인원 정보(OA-12912, 일별), 2025년 1~12월. 공원 둘레 16개 정류장(서울시 실시간 도시데이터 '올림픽공원' 구역의 정류장)만.
- 따릉이: 서울특별시 공공자전거 대여이력 정보(OA-15182), 2025년. 공원 둘레 12개 대여소에서 빌렸거나 반납한 것만. 자전거 번호는 버리고, 태어난 해는 10년 단위로만 남겨요.
결과: analysis/bus_park_2025.csv.gz, analysis/bike_park_2025.csv.gz"""
import csv, gzip, io, os, sys, urllib.request, zipfile
URL = 'https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?useCache=false&infId={inf}&seqNo=&seq={seq}&infSeq={iseq}'
ARS = {'24123', '24127', '24231', '24233', '24239', '24240', '24241', '24244', '24246', '24247', '24396', '24744', '24745', '24901', '24902', '24903'}
BIKE = {'1268', '1267', '2622', '2621', '4857', '5781', '5751', '4862', '4481', '4865', '4464', '4856'}
def get(inf, seq, iseqs=(1, 2, 3)):
    for iseq in iseqs:
        u = URL.format(inf=inf, seq=seq, iseq=iseq)
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=600) as r:
                b = r.read()
            if len(b) > 100000: print(inf, seq, 'infSeq', iseq, len(b), 'bytes', flush=True); return b
        except Exception as e: print(inf, seq, iseq, 'fail', e, flush=True)
    raise SystemExit('download failed %s %s' % (inf, seq))
def rows(b):
    for enc in ('utf-8-sig', 'cp949'):
        try: t = b.decode(enc); break
        except UnicodeDecodeError: continue
    return csv.reader(io.StringIO(t))
what = sys.argv[1:] or ['bus', 'bike']
if 'bus' in what:
    out = gzip.open('analysis/bus_park_2025.csv.gz', 'wt', encoding='utf-8', newline=''); w = csv.writer(out)
    w.writerow(['date', 'route', 'ars', 'stop', 'on', 'off']); n = 0
    for seq in range(142, 154):
        R = rows(get('OA-12912', seq, (3, 1, 2))); h = next(R); print('header', h, flush=True)
        ix = {k: next(i for i, c in enumerate(h) if k in c.replace(' ', '')) for k in ('사용일자', '노선번호', 'ARS', '역명', '승차', '하차')}
        for r in R:
            if len(r) > ix['ARS'] and r[ix['ARS']].strip() in ARS:
                w.writerow([r[ix['사용일자']].strip(), r[ix['노선번호']].strip(), r[ix['ARS']].strip(), r[ix['역명']].strip(), r[ix['승차']].strip(), r[ix['하차']].strip()]); n += 1
    out.close(); print('bus rows', n, flush=True)
if 'bike' in what:
    z = zipfile.ZipFile(io.BytesIO(get('OA-15182', 96)))
    out = gzip.open('analysis/bike_park_2025.csv.gz', 'wt', encoding='utf-8', newline=''); w = csv.writer(out)
    w.writerow(['rent_time', 'rent_station', 'return_time', 'return_station', 'minutes', 'meters', 'birth_decade', 'sex', 'user_type']); n = 0
    for name in z.namelist():
        if not name.lower().endswith('.csv'): continue
        b = z.read(name); R = rows(b); h = next(R); print(name, 'header', h, flush=True)
        def col(*keys):
            for i, c in enumerate(h):
                cc = c.replace(' ', '')
                if all(k in cc for k in keys): return i
            return None
        rt, rs, tt, ts, mi, me, by, sx, ut = col('대여일시'), col('대여', '대여소번호'), col('반납일시'), col('반납', '대여소번호'), col('이용시간'), col('이용거리'), col('생년'), col('성별'), col('이용자종류')
        for r in R:
            try:
                a, c = r[rs].strip().lstrip("'"), r[ts].strip().lstrip("'")
            except (IndexError, TypeError): continue
            if a in BIKE or c in BIKE:
                yb = r[by].strip() if by is not None and by < len(r) else ''
                dec = (yb[:3] + '0') if yb.isdigit() and len(yb) == 4 else ''
                w.writerow([r[rt].strip(), a, r[tt].strip(), c, r[mi].strip() if mi is not None else '', r[me].strip() if me is not None else '', dec, r[sx].strip() if sx is not None and sx < len(r) else '', r[ut].strip() if ut is not None and ut < len(r) else '']); n += 1
    out.close(); print('bike rows', n, flush=True)
