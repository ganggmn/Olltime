/* GET /api/kopis?from=YYYYMMDD&to=YYYYMMDD : 공연예술통합전산망(KOPIS) '공연시설별 통계'에서 올림픽공원 공연장들의
   티켓 판매수(totnmrs), 좌석수, 상연횟수를 받아 와요. 공연 규모를 미리 알아 공연 날 인원 예측의 크기를 맞추려는 용도예요.
   키는 서버에만 있어요(KOPIS_KEY, 1인 1개라 남과 나누지 않음). 남이 이 주소로 키를 마음대로 쓰지 못하게
   시설 이름은 아래 목록에서만 고르고, 기간은 KOPIS 제한대로 31일까지만 받아요. 결과에는 KOPIS 출처를 붙여요. */
export const NAMES = ['올림픽공원', 'KSPO', '체조경기장', '핸드볼', '올림픽홀', '티켓링크'];
const SOURCE = '공연예술통합전산망(KOPIS) 공연시설별 통계';
const day = s => { if (!/^\d{8}$/.test(s || '')) return null; const t = Date.UTC(+s.slice(0, 4), +s.slice(4, 6) - 1, +s.slice(6, 8)); const d = new Date(t); return d.getUTCDate() === +s.slice(6, 8) && d.getUTCMonth() === +s.slice(4, 6) - 1 ? t : null; };
const kstToday = () => { const k = new Date(Date.now() + 9 * 3600e3); return Date.UTC(k.getUTCFullYear(), k.getUTCMonth(), k.getUTCDate()); };
export function range(from, to) {
  const a = day(from), b = day(to);
  if (a === null || b === null) return '날짜는 20251122처럼 8자리로 적어 주세요';
  if (b < a) return '끝 날짜가 시작 날짜보다 앞이에요';
  if ((b - a) / 864e5 + 1 > 31) return 'KOPIS는 한 번에 31일까지만 조회돼요';
  if (a < Date.UTC(2019, 0, 1) || b > kstToday() + 365 * 864e5) return '조회할 수 없는 기간이에요';
  return null;
}
const unesc = s => s.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&').trim();
const TEXT = new Set(['prfnmfct', 'prfnmplc', 'fcltynm', 'prfplcnm', 'errmsg', 'returncode', 'returnmsg']);
export function parse(xml) {
  return [...xml.matchAll(/<(db|prfst)>([\s\S]*?)<\/\1>/g)].map(m => Object.fromEntries([...m[2].matchAll(/<(\w+)>([\s\S]*?)<\/\1>/g)].map(([, k, v]) => { v = unesc(v); const n = v.replace(/,/g, ''); return [k, !TEXT.has(k) && /^-?\d+(\.\d+)?$/.test(n) ? +n : v]; })));
}
export default async function handler(req, res) {
  const { KOPIS_KEY } = process.env, q = req.query || {};
  if (!KOPIS_KEY) { res.setHeader('Cache-Control', 'no-store'); return res.status(503).json({ ok: false, note: 'KOPIS 키가 아직 연결되지 않았어요' }); }
  const from = String(q.from || ''), to = String(q.to || q.from || ''), name = String(q.q || '올림픽공원');
  const bad = range(from, to) || (NAMES.includes(name) ? null : '시설 이름은 ' + NAMES.join(', ') + ' 중에서만 골라요');
  if (bad) { res.setHeader('Cache-Control', 'no-store'); return res.status(400).json({ ok: false, note: bad }); }
  const hide = t => String(t).split(KOPIS_KEY).join('***').split(encodeURIComponent(KOPIS_KEY)).join('***');
  const path = `/openApi/restful/prfstsPrfByFct?service=${encodeURIComponent(KOPIS_KEY)}&stdate=${from}&eddate=${to}&cpage=1&rows=100&shprfnmfct=${encodeURIComponent(name)}`;
  let xml = null, why = '', via = '';
  for (const host of ['https://www.kopis.or.kr', 'http://www.kopis.or.kr']) {
    try { const r = await fetch(host + path, { signal: AbortSignal.timeout(8000) }); if (!r.ok) { why = `서버 응답 ${r.status}`; continue; } xml = await r.text(); via = host.split(':')[0]; break; } catch (e) { why = 'KOPIS에 닿지 못했어요'; }
  }
  res.setHeader('Cache-Control', 'no-store');
  if (xml === null) return res.status(502).json({ ok: false, note: why });
  if (!/<(dbs?|prfsts?)[\s>]/.test(xml)) return res.status(502).json({ ok: false, note: '형식이 다른 응답이에요', head: hide(xml.slice(0, 300)) });
  const rows = parse(xml), err = rows.find(r => r.errmsg || (r.returncode !== undefined && String(r.returncode) !== '00'));
  if (err) return res.status(502).json({ ok: false, note: 'KOPIS가 오류를 돌려줬어요', err: hide(JSON.stringify(err)).slice(0, 200) });
  res.setHeader('Cache-Control', day(to) < kstToday() ? 's-maxage=86400' : 's-maxage=600');
  const out = { ok: true, source: SOURCE, from, to, q: name, via, read_at: new Date().toISOString(), rows };
  if (q.raw === '1') out.raw = hide(xml.slice(0, 4000));
  return res.status(200).json(out);
}
