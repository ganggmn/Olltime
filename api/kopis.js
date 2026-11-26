/* GET /api/kopis?from=YYYYMMDD&to=YYYYMMDD : 공연예술통합전산망(KOPIS) '공연시설별 통계'에서 올림픽공원 공연장들의
   티켓 판매수(totnmrs), 좌석수, 상연횟수를 받아 와요. 공연 규모를 미리 알아 공연 날 인원 예측의 크기를 맞추려는 용도예요.
   키는 서버에만 있어요(KOPIS_KEY, 1인 1개라 남과 나누지 않음). 남이 이 주소로 키를 마음대로 쓰지 못하게
   시설 이름은 아래 목록에서만 고르고, 기간은 KOPIS 제한대로 31일까지만 받아요. 결과에는 KOPIS 출처를 붙여요.
   t=list(공연 목록, 같은 시설·기간, page=1~20)와 t=detail&id=PF…(공연 상세: 공연 시각, 가격, 장르)도 받아요. */
export const NAMES = ['올림픽공원', 'KSPO', '체조경기장', '핸드볼', '올림픽홀', '티켓링크'];
const SOURCE = { fct: '공연예술통합전산망(KOPIS) 공연시설별 통계', list: '공연예술통합전산망(KOPIS) 공연목록', detail: '공연예술통합전산망(KOPIS) 공연상세' };
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
const NUM = new Set(['seatcnt', 'prfcnt', 'prfprocnt', 'prfdtcnt', 'totnmrs']);
export function parse(xml) {
  return [...xml.matchAll(/<(db|prfst)>([\s\S]*?)<\/\1>/g)].map(m => Object.fromEntries([...m[2].matchAll(/<(\w+)>([\s\S]*?)<\/\1>/g)].map(([, k, v]) => { v = unesc(v); const n = v.replace(/,/g, ''); return [k, NUM.has(k) && /^-?\d+(\.\d+)?$/.test(n) ? +n : v]; })));
}
export default async function handler(req, res) {
  const { KOPIS_KEY } = process.env, q = req.query || {};
  if (!KOPIS_KEY) { res.setHeader('Cache-Control', 'no-store'); return res.status(503).json({ ok: false, note: 'KOPIS 키가 아직 연결되지 않았어요' }); }
  const t = String(q.t || 'fct'), from = String(q.from || ''), to = String(q.to || q.from || ''), name = String(q.q || '올림픽공원'), id = String(q.id || ''), page = String(q.page || '1');
  const bad = !['fct', 'list', 'detail'].includes(t) ? '조회 종류는 fct(판매수), list(공연 목록), detail(공연 상세)만 돼요'
    : t === 'detail' ? (/^PF\d{4,9}$/.test(id) ? null : '공연 번호는 PF로 시작해요')
    : range(from, to) || (NAMES.includes(name) ? null : '시설 이름은 ' + NAMES.join(', ') + ' 중에서만 골라요') || (/^([1-9]|1\d|20)$/.test(page) ? null : '쪽 번호는 1~20');
  if (bad) { res.setHeader('Cache-Control', 'no-store'); return res.status(400).json({ ok: false, note: bad }); }
  const hide = x => String(x).split(KOPIS_KEY).join('***').split(encodeURIComponent(KOPIS_KEY)).join('***');
  const key = encodeURIComponent(KOPIS_KEY);
  const path = t === 'detail' ? `/openApi/restful/pblprfr/${id}?service=${key}`
    : t === 'list' ? `/openApi/restful/pblprfr?service=${key}&stdate=${from}&eddate=${to}&cpage=${page}&rows=100&shprfnmfct=${encodeURIComponent(name)}`
    : `/openApi/restful/prfstsPrfByFct?service=${key}&stdate=${from}&eddate=${to}&cpage=1&rows=100&shprfnmfct=${encodeURIComponent(name)}`;
  let xml = null, why = '', via = '';
  for (const host of ['https://www.kopis.or.kr', 'http://www.kopis.or.kr']) {
    try { const r = await fetch(host + path, { signal: AbortSignal.timeout(8000) }); if (!r.ok) { why = `서버 응답 ${r.status}`; continue; } xml = await r.text(); via = host.split(':')[0]; break; } catch (e) { why = 'KOPIS에 닿지 못했어요'; }
  }
  res.setHeader('Cache-Control', 'no-store');
  if (xml === null) return res.status(502).json({ ok: false, note: why });
  const empty = !xml.trim() || /<(dbs|prfsts)\s*\/>/.test(xml) || /<(dbs|prfsts)>\s*<\/\1>/.test(xml);
  if (!empty && !/<(dbs?|prfsts?)[\s>]/.test(xml)) return res.status(502).json({ ok: false, note: '형식이 다른 응답이에요', head: hide(xml.slice(0, 300)) });
  const rows = parse(xml), err = rows.find(r => r.errmsg || (r.returncode !== undefined && String(r.returncode) !== '00'));
  if (err) return res.status(502).json({ ok: false, note: 'KOPIS가 오류를 돌려줬어요', err: hide(JSON.stringify(err)).slice(0, 200) });
  res.setHeader('Cache-Control', t !== 'fct' || day(to) < kstToday() ? 's-maxage=86400' : 's-maxage=600');
  const out = { ok: true, source: SOURCE[t], t, from, to, q: name, ...(t === 'detail' ? { id } : {}), via, read_at: new Date().toISOString(), rows, ...(rows.length ? {} : { note: '그 기간에는 KOPIS 자료가 없어요' }) };
  if (q.raw === '1') out.raw = hide(xml.slice(0, 4000));
  return res.status(200).json(out);
}
