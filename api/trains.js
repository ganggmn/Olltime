/* GET /api/trains: 공원 둘레 세 역(올림픽공원 5·9호선, 한성백제 9호선, 몽촌토성 8호선)에 들어오는 열차를 1분마다 받아 저장해요.
   예약 작업이 1분마다 불러요. 사람 수는 오지 않고, 열차가 언제 도착·출발했는지(서울시가 정보를 만든 시각, 초 단위)가 와요.
   공연 뒤 열차 간격·임시 열차·막차를 기지국 인구의 변화와 맞대 보려는 용도예요. 키는 서버에만 있어요(SEOUL_SUBWAY_KEY). */
import { ask } from './_subway.js';
const Q = ['올림픽공원', '올림픽공원(한국체대)', '한성백제', '몽촌토성(평화의문)'];
export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  const { SEOUL_SUBWAY_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, COLLECT_TOKEN } = process.env;
  if (!SEOUL_SUBWAY_KEY || !SUPABASE_URL || !SUPABASE_SERVICE_KEY) return res.status(503).json({ ok: false, note: '키나 저장소가 아직 연결되지 않았어요' });
  if (COLLECT_TOKEN && req.headers['x-collect-token'] !== COLLECT_TOKEN) return res.status(401).json({ ok: false });
  const slot = new Date(Math.floor(Date.now() / 60000) * 60000).toISOString();
  const got = await Promise.allSettled(Q.map(q => ask(SEOUL_SUBWAY_KEY, q)));
  const list = got.flatMap(g => (g.status === 'fulfilled' ? g.value : [])).map(t => [t.q, t.id, t.updn, t.no, t.exp ? 1 : 0, t.cd, t.sec, t.at, t.dest, t.last ? 1 : 0]);
  const fail = got.map((g, i) => (g.status === 'fulfilled' ? null : Q[i])).filter(Boolean);
  if (!list.length && fail.length === Q.length) return res.status(502).json({ ok: false, note: '열차 정보를 받지 못했어요' });
  const base = SUPABASE_URL.replace(/\/$/, '');
  try {
    const r = await fetch(`${base}/rest/v1/train_samples?on_conflict=ts`, {
      method: 'POST', headers: { apikey: SUPABASE_SERVICE_KEY, Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' },
      body: JSON.stringify({ ts: slot, list, fail: fail.length ? fail : null }), signal: AbortSignal.timeout(8000)
    });
    if (!r.ok) return res.status(502).json({ ok: false, note: `저장 실패 ${r.status}` });
    return res.status(200).json({ ok: true, ts: slot, n: list.length, fail });
  } catch (e) { return res.status(502).json({ ok: false, note: '저장소에 닿지 못했어요' }); }
}
