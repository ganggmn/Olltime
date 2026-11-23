"""GitHub Actions에서 입출차 원본의 빠진 페이지만 받아요 (맥의 fetch_inout_fast.py와 같은 방식, 같은 파일 형식).
키는 저장소 비밀값 KCISA_KEY_INOUT에서만 읽고, 로그에는 페이지 번호와 줄 수만 남겨요."""
import os
import sys
import threading
import queue

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ApiError, get_key  # noqa: E402
from fetch_inout_fast import PARTS, fetch_page, save_part, to_rows  # noqa: E402

pages = [int(p) for p in os.environ["PAGES"].split()]
key = get_key("KCISA_KEY_INOUT")
PARTS.mkdir(parents=True, exist_ok=True)
q = queue.Queue()
for p in pages:
    q.put(p)
ok, bad, lock = {}, {}, threading.Lock()


def worker():
    while True:
        try:
            p = q.get_nowait()
        except queue.Empty:
            return
        for attempt in range(5):
            try:
                items, _total = fetch_page(key, p)
                rows = to_rows(items)
                if not rows:
                    raise ApiError("빈 페이지")
                save_part(p, rows)
                with lock:
                    ok[p] = len(rows)
                print(f"p{p}: {len(rows)}줄", flush=True)
                break
            except Exception as e:  # noqa: BLE001
                msg = str(e).replace(key, "***")[:120]
                print(f"p{p}: 실패 {attempt + 1}번째 ({type(e).__name__}: {msg})", flush=True)
                bad[p] = msg


ths = [threading.Thread(target=worker) for _ in range(4)]
for t in ths:
    t.start()
for t in ths:
    t.join()
miss = [p for p in pages if p not in ok]
print(f"받음 {len(ok)}/{len(pages)}페이지, 합계 {sum(ok.values())}줄. 못 받음: {miss}", flush=True)
