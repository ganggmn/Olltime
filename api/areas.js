/* GET /api/areas?day=YYYY-MM-DD: 공원 둘레 구역(서울시 실시간 도시데이터 '잠실 관광특구')의 사람 수 범위를 5분 단위로 돌려줘요.
   '잠실 관광특구' 구역은 '올림픽공원' 구역을 통째로 품고 있어서, 같은 시각의 /api/trend 값을 빼면 공원 서쪽 테두리의 사람 수가 나와요.
   2026년 11월 26일부터 모아요. 숫자만 담긴 공개 응답이에요. */
export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const { SUPABASE_URL, SUPABASE_SERVICE_KEY } = process.env;
  if (!SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
    res.setHeader('Cache-Control', 's-maxage=60');
    return res.status(200).json({ ok: false, note: '저장소가 아직 연결되지 않았어요' });
  }
  const kst = new Date(Date.now() + 9 * 3600e3);
  const day = /^\d{4}-\d{2}-\d{2}$/.test(String((req.query || {}).day || '')) ? req.query.day : kst.toISOString().slice(0, 10);
  const from = new Date(`${day}T00:00:00+09:00`).toISOString();
  const to = new Date(Date.parse(from) + 864e5).toISOString();
  const q = `select=ts,area,lo,hi,lvl,err&ts=gte.${encodeURIComponent(from)}&ts=lt.${encodeURIComponent(to)}&order=ts.asc&limit=2000`;
  try {
    const r = await fetch(`${SUPABASE_URL.replace(/\/$/, '')}/rest/v1/area_samples?${q}`, {
      headers: { apikey: SUPABASE_SERVICE_KEY, Authorization: `Bearer ${SUPABASE_SERVICE_KEY}` },
      signal: AbortSignal.timeout(8000)
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const rows = await r.json(), areas = {};
    /* 구역마다 [0시부터 몇 분, 인원 아래, 인원 위, 단계, 못 받은 이유] */
    for (const x of rows) (areas[x.area] = areas[x.area] || []).push([Math.round((Date.parse(x.ts) - Date.parse(from)) / 60000), x.lo, x.hi, x.lvl, x.err]);
    res.setHeader('Cache-Control', 's-maxage=120, stale-while-revalidate=300');
    return res.status(200).json({ ok: true, day, areas });
  } catch (e) {
    res.setHeader('Cache-Control', 's-maxage=30');
    return res.status(502).json({ ok: false, note: '저장소를 읽지 못했어요' });
  }
}
