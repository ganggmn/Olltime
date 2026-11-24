/* 서울시 지하철 실시간 도착정보를 받아 작은 모양으로 줄여요. /api/subway와 /api/collect가 같이 써요. */
export const STATIONS = ['올림픽공원', '올림픽공원(한국체대)'];

export const pick = (r, q) => ({
  q,
  id: String(r.subwayId || ''),
  updn: String(r.updnLine || ''),
  line: String(r.trainLineNm || ''),
  dest: String(r.bstatnNm || ''),
  exp: String(r.btrainSttus || '') === '급행',
  no: String(r.btrainNo || ''),
  sec: Number.parseInt(r.barvlDt, 10) || 0,
  cd: String(r.arvlCd || ''),
  msg: String(r.arvlMsg2 || ''),
  at: String(r.recptnDt || ''),
  last: String(r.lstcarAt || '') === '1',
  ord: String(r.ordkey || ''),
});

export async function ask(key, q) {
  const url = `http://swopenapi.seoul.go.kr/api/subway/${encodeURIComponent(key)}/json/realtimeStationArrival/0/20/${encodeURIComponent(q)}`;
  const r = await fetch(url, { signal: AbortSignal.timeout(8000) });
  const text = (await r.text()).trim();
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  if (text.startsWith('<')) {
    const code = (text.match(/<code>\s*([^<]+?)\s*<\/code>/i) || [])[1] || '?';
    throw new Error(`서울시 응답 ${code}`);
  }
  const body = JSON.parse(text);
  const list = body.realtimeArrivalList;
  if (Array.isArray(list)) return list.map((x) => pick(x, q));
  const em = body.errorMessage || body;
  const code = String(em.code || '?');
  /* 해당 이름으로 잡히는 열차가 없을 때(INFO-200)는 빈 목록이에요 */
  if (code === 'INFO-200') return [];
  throw new Error(`서울시 응답 ${code}`);
}

