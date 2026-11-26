"""KOPIS 공연시설별 통계(티켓 판매수)를 올타임 서버(/api/kopis)를 거쳐 받아 analysis/에 저장해요.
키는 Vercel에만 있고 이 스크립트는 키를 모릅니다. 출처: 공연예술통합전산망(KOPIS).

  python scripts/fetch_kopis.py test       # 몇 날짜만 받아 기준(공연일/예매일)과 미리 나오는지 확인 → analysis/kopis_test.json
  python scripts/fetch_kopis.py 2025       # 2025년 모든 날(하루씩) + 달마다 → analysis/kopis_daily_2025.csv, kopis_monthly_2025.csv
  python scripts/fetch_kopis.py upcoming   # 오늘부터 40일 하루씩 → analysis/kopis_upcoming_<오늘>.csv
  python scripts/fetch_kopis.py range 20241101 20241231   # 정한 기간 하루씩 → analysis/kopis_daily_<시작>_<끝>.csv
"""
import csv, json, os, sys, time, urllib.error, urllib.request, urllib.parse, datetime as dt

BASE = os.environ.get('OLLTIME', 'https://olltime.vercel.app').rstrip('/')
COLS = ['from', 'to', 'prfnmfct', 'prfnmplc', 'seatcnt', 'prfcnt', 'prfprocnt', 'prfdtcnt', 'totnmrs']


def ask(a, b, q='올림픽공원', raw=False, **kw):
    u = f"{BASE}/api/kopis?" + urllib.parse.urlencode({**({'from': a, 'to': b, 'q': q} if a else {}), **kw, **({'raw': '1'} if raw else {})})
    for i in range(3):
        try:
            with urllib.request.urlopen(u, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors='replace')
            if e.code in (400, 503):
                return json.loads(body)
            err = {'ok': False, 'note': f'HTTP {e.code}', 'body': body[:300]}
        except Exception as e:
            err = {'ok': False, 'note': str(e)[:200]}
        time.sleep(2 + 3 * i)
    return err


def rows_of(j, a, b):
    out = []
    for r in j.get('rows') or []:
        x = {'from': a, 'to': b}
        for k in COLS[2:]:
            x[k] = r.get(k, '')
        x['extra'] = json.dumps({k: v for k, v in r.items() if k not in COLS}, ensure_ascii=False)
        out.append(x)
    return out


def save(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLS + ['extra'])
        w.writeheader()
        w.writerows(rows)
    print('저장', path, len(rows), '줄')


def days(a, b):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)


def ymd(d):
    return d.strftime('%Y%m%d')


def main(what):
    kst = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)
    today = kst.date()
    if what == 'test':
        shows = json.load(open('analysis/shows_site_2024-12_2025-12.json', encoding='utf-8'))['list']
        dome = sorted({x['d'] for x in shows if x['venue'] == 'KSPO DOME' and x['d'].startswith('2025-11')})
        pick = [d.replace('-', '') for d in dome[:2]] + ['20251103', '20251104']  # 공연 날 둘 + 11월 평일 둘(공연 없는 날 비교)
        pick += [ymd(today + dt.timedelta(days=i)) for i in range(0, 4)]  # 오늘~3일 뒤(이번 공연 미리 나오는지)
        out = {'read_at': kst.isoformat(), 'base': BASE, 'one_day': {}, 'month': None, 'names': {}}
        for d in pick:
            j = ask(d, d, raw=(d == pick[0]))
            out['one_day'][d] = j
            print(d, j.get('ok'), j.get('note', ''), j.get('body', '')[:200], [(r.get('prfnmplc'), r.get('prfdtcnt'), r.get('totnmrs')) for r in j.get('rows') or []])
            time.sleep(0.5)
        out['month'] = ask('20251101', '20251130')
        print('2025-11 한 달', [(r.get('prfnmplc'), r.get('prfdtcnt'), r.get('totnmrs')) for r in out['month'].get('rows') or []])
        for q in ['KSPO', '체조경기장', '핸드볼', '올림픽홀', '티켓링크']:
            j = ask(pick[0], pick[0], q=q)
            out['names'][q] = j
            print('이름', q, j.get('ok'), [(r.get('prfnmfct'), r.get('prfnmplc'), r.get('totnmrs')) for r in j.get('rows') or []])
            time.sleep(0.5)
        if 'raw' in out['one_day'][pick[0]]:
            print('원문 앞부분:', out['one_day'][pick[0]]['raw'][:1500])
        json.dump(out, open('analysis/kopis_test.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    elif what == '2025':
        rows, bad = [], []
        for d in days(dt.date(2025, 1, 1), dt.date(2025, 12, 31)):
            j = ask(ymd(d), ymd(d))
            if not j.get('ok'):
                bad.append((ymd(d), j.get('note')))
            rows += rows_of(j, ymd(d), ymd(d))
            time.sleep(0.3)
        save('analysis/kopis_daily_2025.csv', rows)
        mon = []
        for m in range(1, 13):
            a = dt.date(2025, m, 1)
            b = (a.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
            mon += rows_of(ask(ymd(a), ymd(b)), ymd(a), ymd(b))
            time.sleep(0.3)
        save('analysis/kopis_monthly_2025.csv', mon)
        print('실패한 날', len(bad), bad[:10])
    elif what == 'upcoming':
        rows = []
        for d in days(today, today + dt.timedelta(days=40)):
            rows += rows_of(ask(ymd(d), ymd(d)), ymd(d), ymd(d))
            time.sleep(0.3)
        save(f'analysis/kopis_upcoming_{ymd(today)}.csv', rows)
    elif what == 'range':
        a, b = (dt.datetime.strptime(x, '%Y%m%d').date() for x in sys.argv[2:4])
        rows = []
        for d in days(a, b):
            rows += rows_of(ask(ymd(d), ymd(d)), ymd(d), ymd(d))
            time.sleep(0.3)
        save(f'analysis/kopis_daily_{ymd(a)}_{ymd(b)}.csv', rows)
    elif what == 'meta':
        y0, y1 = int(sys.argv[2]), int(sys.argv[3])
        seen = {}
        for y in range(y0, y1 + 1):
            for m in range(1, 13):
                a = dt.date(y, m, 1); b = (a.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
                for pg in range(1, 21):
                    j = ask(ymd(a), ymd(b), t='list', page=str(pg)); rows = j.get('rows') or []
                    for r in rows: seen.setdefault(r.get('mt20id'), r)
                    time.sleep(0.3)
                    if len(rows) < 100: break
                print(y, m, '누적', len(seen))
        keep = [k for k in seen if k]  # 목록의 시설명은 '올림픽공원'뿐이라 공연장(KSPO DOME 등)은 상세에서 봐요
        print('목록', len(seen))
        out = []
        for k in keep:
            j = ask(None, None, t='detail', id=k); r = (j.get('rows') or [{}])[0]
            x = {**{'list_' + kk: v for kk, v in seen[k].items()}, **{kk: v for kk, v in r.items() if isinstance(v, (str, int, float)) and '<' not in str(v)}}
            out.append(x); time.sleep(0.3)
        cols = sorted({c for x in out for c in x})
        with open(f'analysis/kopis_meta_{y0}_{y1}.csv', 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(out)
        print('저장', len(out), '공연', cols)
    else:
        sys.exit('test, 2025, upcoming, range, meta 중 하나')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'test')
