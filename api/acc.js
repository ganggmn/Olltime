/* GET /api/acc: 최근 7일 서울시 혼잡 예보 적중률(1~12시간 앞). 저장소(samples)의 예보와 실측으로 계산하고 1시간 동안 CDN에 저장해요.
   응답: { ok, days, horizon: [{ h, n, level }], period: [첫 발표, 마지막 발표] } — 숫자만 담겨요. */
import { forecastHits } from './_acc.js';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const { SUPABASE_URL, SUPABASE_SERVICE_KEY } = process.env;
  if (!SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
    res.setHeader('Cache-Control', 's-maxage=60');
    return res.status(200).json({ ok: false, note: '저장소 연결 없음' });
  }
  const days = Math.max(1, Math.min(14, parseInt(req.query && req.query.days, 10) || 7));
  const from = new Date(Date.now() - days * 864e5).toISOString();
  const base = SUPABASE_URL.replace(/\/$/, '');
  const headers = { apikey: SUPABASE_SERVICE_KEY, Authorization: `Bearer ${SUPABASE_SERVICE_KEY}` };
  try {
    const rows = [];
    for (let off = 0; off < 6000; off += 1000) {
      const q = `select=ppl_time,lvl,fcst&ts=gte.${encodeURIComponent(from)}&order=ts.asc&limit=1000&offset=${off}`;
      const r = await fetch(`${base}/rest/v1/samples?${q}`, { headers, signal: AbortSignal.timeout(8000) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const part = await r.json();
      rows.push(...part);
      if (part.length < 1000) break;
    }
    const out = forecastHits(rows);
    res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate=86400');
    return res.status(200).json({ ok: true, days, ...out });
  } catch (e) {
    res.setHeader('Cache-Control', 's-maxage=60');
    return res.status(502).json({ ok: false, note: '저장소 읽기 실패' });
  }
}
