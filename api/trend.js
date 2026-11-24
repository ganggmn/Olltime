/* GET /api/trend: 오늘(한국 시간 0시부터) 쌓인 주차 대수와 공원 인원 범위를 5분 단위로 돌려줘요.
   저장소 키는 서버에만 있고, 응답에는 숫자만 들어 있어요. 2분 동안 CDN에 저장해요. */
export default async function handler(req, res) {
  const { SUPABASE_URL, SUPABASE_SERVICE_KEY } = process.env;
  if (!SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
    res.setHeader('Cache-Control', 's-maxage=60');
    return res.status(200).json({ ok: false, note: '저장소가 아직 연결되지 않았어요' });
  }
  const kst = new Date(Date.now() + 9 * 3600e3);
  const day = /^\d{4}-\d{2}-\d{2}$/.test(String(req.query.day || '')) ? req.query.day : kst.toISOString().slice(0, 10);
  const from = new Date(`${day}T00:00:00+09:00`).toISOString();
  const to = new Date(Date.parse(from) + 864e5).toISOString();
  const q = `select=ts,parking,ppl_lo,ppl_hi,lvl&ts=gte.${encodeURIComponent(from)}&ts=lt.${encodeURIComponent(to)}&order=ts.asc&limit=400`;
  try {
    const r = await fetch(`${SUPABASE_URL.replace(/\/$/, '')}/rest/v1/samples?${q}`, {
      headers: { apikey: SUPABASE_SERVICE_KEY, Authorization: `Bearer ${SUPABASE_SERVICE_KEY}` },
      signal: AbortSignal.timeout(8000)
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const rows = await r.json();
    /* [0시부터 몇 분, 주차 대수, 인원 아래, 인원 위, 단계] */
    const list = rows.map(x => [Math.round((Date.parse(x.ts) - Date.parse(from)) / 60000), x.parking, x.ppl_lo, x.ppl_hi, x.lvl]);
    res.setHeader('Cache-Control', 's-maxage=120, stale-while-revalidate=300');
    return res.status(200).json({ ok: true, day, n: list.length, list });
  } catch (e) {
    res.setHeader('Cache-Control', 's-maxage=30');
    return res.status(502).json({ ok: false, note: '저장소를 읽지 못했어요' });
  }
}
