/* GET /api/buses: 공원 둘레 세 정류장(올림픽공원역 24244, 올림픽공원남2문 24240, 몽촌토성역 24127)에 들어오는 버스의
   차내 혼잡도(서울시가 교통카드 승·하차로 재차인원을 세어 '여유·보통·혼잡'으로 매긴 값)를 받아 저장해요.
   예약 작업이 2분마다 불러요. 공공데이터포털 개발 계정은 하루 1,000번까지라, 저녁 5시~밤 12시(한국 시각)에는 2분마다,
   그 밖에는 10분마다만 실제로 물어봐요(하루 약 940번). 키는 서버에만 있어요(DATA_GO_KR_KEY). */
const STOPS = [['24244', '올림픽공원역'], ['24240', '올림픽공원남2문'], ['24127', '몽촌토성역']];
export const due = d => { const k = new Date(d.getTime() + 9 * 3600e3), h = k.getUTCHours(), m = k.getUTCMinutes(); return h >= 17 ? true : m % 10 === 0; };
const keyParam = k => (/%[0-9A-Fa-f]{2}/.test(k) ? k : encodeURIComponent(k));
export async function stop(key, ars) {
  const u = `http://ws.bus.go.kr/api/rest/stationinfo/getStationByUid?serviceKey=${keyParam(key)}&arsId=${ars}&resultType=json`;
  const r = await fetch(u, { signal: AbortSignal.timeout(8000) });
  if (!r.ok) throw new Error(`서버 응답 ${r.status}`);
  const j = JSON.parse(await r.text()), hd = j.msgHeader || {};
  if (String(hd.headerCd ?? '0') !== '0') throw new Error(`결과 코드 ${hd.headerCd}`);
  const n = v => (v === undefined || v === null || v === '' ? null : +v);
  return (j.msgBody?.itemList || []).map(x => [ars, x.rtNm, x.busRouteId, x.vehId1 === '0' ? null : x.vehId1, n(x.traTime1), n(x.isArrive1), n(x.congestion1), n(x.rerdieDiv1), n(x.rerideNum1), n(x.isFullFlag1), x.vehId2 === '0' ? null : x.vehId2, n(x.traTime2), n(x.congestion2), n(x.rerdieDiv2), n(x.rerideNum2)]);
}
export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  const { DATA_GO_KR_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, COLLECT_TOKEN } = process.env;
  if (!DATA_GO_KR_KEY || !SUPABASE_URL || !SUPABASE_SERVICE_KEY) return res.status(503).json({ ok: false, note: '키나 저장소가 아직 연결되지 않았어요' });
  if (COLLECT_TOKEN && req.headers['x-collect-token'] !== COLLECT_TOKEN) return res.status(401).json({ ok: false });
  const now = new Date(), slot = new Date(Math.floor(now.getTime() / 60000) * 60000);
  if (!due(slot) && req.query?.force !== '1') return res.status(200).json({ ok: true, skipped: true });
  const got = await Promise.allSettled(STOPS.map(([a]) => stop(DATA_GO_KR_KEY, a)));
  const list = got.flatMap(g => (g.status === 'fulfilled' ? g.value : []));
  const hide = t => String(t).split(DATA_GO_KR_KEY).join('***').split(keyParam(DATA_GO_KR_KEY)).join('***');
  const fail = got.map((g, i) => (g.status === 'fulfilled' ? null : `${STOPS[i][0]} ${hide(g.reason?.message || g.reason).slice(0, 60)}`)).filter(Boolean);
  if (!list.length && fail.length === STOPS.length) return res.status(502).json({ ok: false, note: '버스 정보를 받지 못했어요', fail });
  const base = SUPABASE_URL.replace(/\/$/, '');
  try {
    const r = await fetch(`${base}/rest/v1/bus_samples?on_conflict=ts`, {
      method: 'POST', headers: { apikey: SUPABASE_SERVICE_KEY, Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' },
      body: JSON.stringify({ ts: slot.toISOString(), list, fail: fail.length ? fail : null }), signal: AbortSignal.timeout(8000)
    });
    if (!r.ok) return res.status(502).json({ ok: false, note: `저장 실패 ${r.status}` });
    return res.status(200).json({ ok: true, ts: slot.toISOString(), n: list.length, fail });
  } catch (e) { return res.status(502).json({ ok: false, note: '저장소에 닿지 못했어요' }); }
}
