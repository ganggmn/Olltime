"""서울교통공사 역별 승하차인원 API(공공데이터포털 15143845)로 올림픽공원·몽촌토성·한성백제역의 시간대별 승하차를 받아요.

이 API는 최근 일주일치만 줘요. 그래서 공연 날(11/27~29)이 지나기 전에 받아 두어야 해요.
키: .env의 DATA_GO_KR_KEY (이미 쓰는 공공데이터포털 키). 활용신청이 승인돼 있어야 해요.
화면에는 키가 나오지 않아요(common.http_get이 가림).

사용법:
    python3 fetch_psgr.py                      최근 7일(오늘 빼고)
    python3 fetch_psgr.py 20261127 20261128    정한 날만
이미 받은 날은 건너뛰어요.

저장 위치 data/psgr/
    YYYYMMDD.csv           세 역 줄만(받은 그대로의 항목)
    YYYYMMDD_hour.csv      호선·역·시간대별 승차(rideNope)·하차(gffNope) 합계
이 API는 1~8호선만 있어요(9호선 올림픽공원·한성백제는 없음).
    _schema.txt            처음 받은 응답의 항목 이름(키 없음)
"""
import csv
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta

from common import DATA, ApiError, extract, get_key, http_get, load_env, parse_body

OUT = DATA / "psgr"
WORDS = ["올림픽공원", "몽촌토성", "한성백제"]
BASE = "https://apis.data.go.kr/B553766/psgr"
OPS = ["/getStnPsgr", "", "/getPsgr", "/getPsgrInfo"]  # 2026-11-28에 /getStnPsgr로 확인
ROWS = 1000


def get_page(key, op, ymd, page):
    params = {"serviceKey": key, "pageNo": page, "numOfRows": ROWS, "dataType": "JSON", "pasngYmd": ymd}
    return parse_body(http_get(BASE + op, params, timeout=60))


def find_op(key, ymd):
    last = None
    for op in OPS:
        try:
            obj = get_page(key, op, ymd, 1)
            items, total = extract(obj)
            return op, obj, items, total
        except ApiError as e:
            last = e
            if "인증 오류" in str(e):  # 키·승인 문제면 다른 주소를 시험해도 같아요
                raise
    raise ApiError(f"맞는 주소를 못 찾았어요(마지막 오류: {last})")


def pick(row):
    s = " ".join(str(v) for v in row.values())
    return any(w in s for w in WORDS)


def guess(row, *names):
    up = {str(k).upper(): k for k in row}
    for n in names:
        for u, k in up.items():
            if n in u:
                return k
    return None


def write_hour(ymd):
    src = OUT / f"{ymd}.csv"
    if not src.exists():
        return
    agg = defaultdict(lambda: [0, 0])
    with open(src, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            k = (r.get("lineNm", ""), r.get("stnNm", ""), r.get("pasngHr", ""))
            agg[k][0] += float(r.get("rideNope") or 0)
            agg[k][1] += float(r.get("gffNope") or 0)
    with open(OUT / f"{ymd}_hour.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["호선", "역", "시간대", "승차", "하차"])
        for (ln, st, hr), (on, off) in sorted(agg.items()):
            w.writerow([ln, st, hr, round(on), round(off)])


def main():
    load_env()
    key = get_key("DATA_GO_KR_KEY")
    OUT.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1:
        days = sys.argv[1:]
    else:
        today = datetime.now()
        days = [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(7, 0, -1)]
    op = None
    for ymd in days:
        if (OUT / f"{ymd}.csv").exists():
            print(f"{ymd}: 이미 있어요, 건너뜀")
            continue
        try:
            if op is None:
                op, obj, items, total = find_op(key, ymd)
                print(f"주소 확인: {BASE}{op or ''}")
                if items:
                    (OUT / "_schema.txt").write_text("항목: " + ", ".join(map(str, items[0].keys())) + "\n", encoding="utf-8")
            else:
                obj = get_page(key, op, ymd, 1)
                items, total = extract(obj)
        except ApiError as e:
            print(f"{ymd}: 실패 — {e}")
            continue
        pages = 1 if not total else (total + ROWS - 1) // ROWS
        print(f"{ymd}: 전체 {total}줄, {pages}쪽 받는 중", end="", flush=True)
        kept = [r for r in items if pick(r)]
        for p in range(2, pages + 1):
            for tryno in range(3):
                try:
                    more, _ = extract(get_page(key, op, ymd, p))
                    kept += [r for r in more if pick(r)]
                    break
                except ApiError as e:
                    if tryno == 2:
                        print(f"\n  {p}쪽 실패: {e}")
                    time.sleep(2)
            if p % 20 == 0:
                print(".", end="", flush=True)
        print(f" → 세 역 {len(kept)}줄")
        if not kept:
            continue
        fields = sorted({k for r in kept for k in r})
        with open(OUT / f"{ymd}.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(kept)
        write_hour(ymd)
    # 앞서 받은 날도 시간대 합계를 다시 만들어요(항목 이름: 역 stnNm, 시간 pasngHr, 승차 rideNope, 하차 gffNope)
    for f in sorted(OUT.glob("2*.csv")):
        if not f.stem.endswith("_hour"):
            write_hour(f.stem)
    print("\n끝났어요. 결과는 data/psgr/ 폴더에 있어요. 실패가 '인증 오류'면 공공데이터포털에서 15143845 활용신청 승인 여부를 봐 주세요.")


if __name__ == "__main__":
    main()
