"""새 공공데이터 4가지의 모양을 확인해요(GitHub 자동 작업에서 한 번 돌림). 결과는 작업 기록에만 찍고 파일은 남기지 않아요.
1) 수도권 생활이동 도착 행정동 기준 시간대별 성연령별 수단(내국인, OA-22655, 월별)
2) 수도권 생활이동 출도착 행정동별 수단(OA-22657, 일별)  3) 연령대별 출도착 행정동별 수단(내국인, OA-22658, 일별)
4) [단기외국인] 행정동별 서울 생활인구(250m)(OA-23018, 월별)  5) TOPIS 지점별 일자별 교통량(2025년 1월)"""
import csv, io, sys, urllib.request, urllib.parse, zipfile
URL = 'https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?useCache=false&infId={inf}&seqNo=&seq={seq}&infSeq={iseq}'
UA = {'User-Agent': 'Mozilla/5.0'}
KEYS = ('11710566', '1171066', '오륜')
def get(inf, seq):
    for iseq in (1, 2, 3):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL.format(inf=inf, seq=seq, iseq=iseq), headers=UA), timeout=900) as r: b = r.read()
            if len(b) > 10000: print(inf, seq, 'infSeq', iseq, len(b), 'bytes', flush=True); return b
            print(inf, seq, iseq, 'small', len(b), b[:200], flush=True)
        except Exception as e: print(inf, seq, iseq, 'fail', e, flush=True)
def show(inf, seq, n=4):
    b = get(inf, seq)
    if not b: return
    z = zipfile.ZipFile(io.BytesIO(b)); print(' files', [(i.filename, i.file_size) for i in z.infolist()][:8], flush=True)
    for name in z.namelist()[:2]:
        raw = z.read(name)
        for enc in ('utf-8-sig', 'cp949'):
            try: t = raw.decode(enc); break
            except UnicodeDecodeError: continue
        lines = t.splitlines(); print(' ', name, enc, len(lines), 'lines', flush=True)
        for l in lines[:n]: print('   ', l[:400], flush=True)
        hit = [l for l in lines if any(k in l for k in KEYS)]
        print('  오륜동 행', len(hit), flush=True)
        for l in hit[:6]: print('   ', l[:400], flush=True)
what = sys.argv[1:] or ['m', 'od', 'od4', 'fo', 'topis']
if 'm' in what: show('OA-22655', '202511')
if 'od' in what: show('OA-22657', '251122')
if 'od4' in what: show('OA-22658', '251122', 3)
if 'fo' in what: show('OA-23018', '202511')
if 'topis' in what:
    f = dict(apndFileNm='01월 서울시 교통량 조사자료(2025).xlsx', apndFilePathNm='174055413809421952746758349263.xlsx', bdwrSeq='4679', blbdDivCd='08')
    for how in ('post', 'get'):
        try:
            data = urllib.parse.urlencode(f).encode()
            req = urllib.request.Request('https://topis.seoul.go.kr/downloadFileRefRoom.do', data=data if how == 'post' else None, headers=dict(UA, Referer='https://topis.seoul.go.kr/refRoom/openRefRoom_2.do'))
            if how == 'get': req = urllib.request.Request('https://topis.seoul.go.kr/downloadFileRefRoom.do?' + urllib.parse.urlencode(f), headers=dict(UA, Referer='https://topis.seoul.go.kr/refRoom/openRefRoom_2.do'))
            with urllib.request.urlopen(req, timeout=300) as r: b = r.read()
            print('topis', how, len(b), b[:4], flush=True)
            if b[:2] == b'PK':
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True); print(' sheets', wb.sheetnames, flush=True)
                for ws in wb.worksheets[:3]:
                    rows = list(ws.iter_rows(max_row=4, values_only=True)); print(' ', ws.title, rows, flush=True)
                for ws in wb.worksheets:
                    names = set()
                    for r in ws.iter_rows(values_only=True):
                        s = ' '.join(str(x) for x in r if x is not None)
                        if any(k in s for k in ('올림픽', '양재대로', '강동대로', '송파', '천호', '잠실', '방이', '성내', '풍납', '오금')): names.add(s[:120])
                        if len(names) > 60: break
                    print(' 공원 근처 후보', ws.title, sorted(names)[:60], flush=True)
                break
        except Exception as e: print('topis', how, 'fail', e, flush=True)
