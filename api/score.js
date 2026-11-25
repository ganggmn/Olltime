/* GET /api/score: 쌓인 실제 값으로 '2시간 앞서 낸 예상'을 날마다 다시 채점해요.
   ?days=7(1~14) &end=YYYY-MM-DD(기본 오늘) &win=분 &dn=명 &dp=% &k=배  ← 이상 징후 기준(운영자가 정함, 비우면 안 씀)
   계산은 model.js의 scoreDays 하나로 해요. 같은 기록(/api/trend)과 같은 파일로 누구나 같은 숫자를 낼 수 있어요(analysis/live_score.mjs). */
import '../gp.js';
import '../model.js';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const { SUPABASE_URL, SUPABASE_SERVICE_KEY } = process.env;
  if (!SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
    res.setHeader('Cache-Control', 's-maxage=60');
    return res.status(200).json({ ok: false, note: '저장소가 아직 연결되지 않았어요' });
  }
  const q = req.query || {};
  const OLL = globalThis.OLL;
  const kst = new Date(Date.now() + 9 * 3600e3);
  const end = /^\d{4}-\d{2}-\d{2}$/.test(String(q.end || '')) ? q.end : kst.toISOString().slice(0, 10);
  const days = Math.min(14, Math.max(1, Math.round(Number(q.days) || 7)));
  const rules = OLL.cleanRules(q);
  const list = [];
  for (let i = days - 1; i >= 0; i--) list.push(new Date(Date.parse(end + 'T00:00:00Z') - i * 864e5).toISOString().slice(0, 10));
  const base = SUPABASE_URL.replace(/\/$/, '');
  const one = async day => {
    const from = new Date(`${day}T00:00:00+09:00`).toISOString(), to = new Date(Date.parse(from) + 864e5).toISOString();
    const r = await fetch(`${base}/rest/v1/samples?select=ts,parking,ppl_lo,ppl_hi,lvl&ts=gte.${encodeURIComponent(from)}&ts=lt.${encodeURIComponent(to)}&order=ts.asc&limit=400`, {
      headers: { apikey: SUPABASE_SERVICE_KEY, Authorization: `Bearer ${SUPABASE_SERVICE_KEY}` }, signal: AbortSignal.timeout(8000)
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return (await r.json()).map(x => [Math.round((Date.parse(x.ts) - Date.parse(from)) / 60000), x.parking, x.ppl_lo, x.ppl_hi, x.lvl]);
  };
  try {
    const rows = await Promise.all(list.map(one));
    const byDay = {};
    list.forEach((d, i) => { if (rows[i].length) byDay[d] = rows[i]; });
    const out = OLL.scoreDays(byDay, rules);
    res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600');
    return res.status(200).json({ ok: true, end, asked: days, ...out });
  } catch (e) {
    res.setHeader('Cache-Control', 's-maxage=30');
    return res.status(502).json({ ok: false, note: '저장소를 읽지 못했어요' });
  }
}
