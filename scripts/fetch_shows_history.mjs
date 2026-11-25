/* 지난 공연 일정을 올림픽공원 누리집 '일정안내'에서 받아 저장해요(분석용). 
   사용: node scripts/fetch_shows_history.mjs 2025-01 2025-12  → analysis/shows_site_2025.json
   원문(시각 문장 포함)과, api/_shows.js로 풀어 낸 날짜별 시작 시각을 함께 남겨요. */
import fs from 'fs';
import { parseShows, timesOf, venueOf, runOf } from '../api/_shows.js';
const [a = '2025-01', b = '2025-12'] = process.argv.slice(2);
const yms = []; for (let y = +a.slice(0, 4), m = +a.slice(5, 7); y * 12 + m <= +b.slice(0, 4) * 12 + +b.slice(5, 7); m++) { if (m > 12) { m = 1; y++; } yms.push(String(y) + String(m).padStart(2, '0')); }
const raw = [], seen = new Set();
for (const ym of yms) {
  const r = await fetch('https://www.ksponco.or.kr/olympicpark/eventInfo/eventInfoListAjax.es', { method: 'POST', headers: { 'Content-Type': 'application/json;charset=UTF-8' }, body: JSON.stringify({ nowYM: ym, plcCd: '' }) });
  const j = await r.json();
  for (const g of j) for (const x of g) { if (seen.has(x.evtSeq)) continue; seen.add(x.evtSeq); raw.push({ evtSeq: x.evtSeq, plc: x.plc, plcCd: (x.plcCd || '').trim(), beginDt: x.beginDt, endDt: x.endDt, ndTm: x.ndTm, seeAge: x.seeAge, title: x.title, tm: x.tm, genre: x.goodsCd ? 'ticket' : '' }); }
}
raw.sort((p, q) => (p.beginDt < q.beginDt ? -1 : 1));
const parsed = parseShows([[raw]]);
/* 작은 공연장도 시각을 풀어 둠(분석에서 거를 수 있게) */
const small = [];
for (const x of raw) if (!venueOf(x.plc)) { const t = timesOf(x.tm, x.beginDt, x.endDt); for (const s of t.list) small.push({ d: s.d, t: s.t, venue: String(x.plc || '').trim(), name: String(x.title || '').trim(), run: runOf(x.ndTm), seq: x.evtSeq }); }
const out = { source: '한국체육산업개발 올림픽공원 누리집 일정안내 (eventInfoListAjax.es)', read_at: new Date().toISOString(), months: yms, raw, list: parsed.list, small, skipped: parsed.skipped };
fs.writeFileSync('analysis/shows_site_' + a.slice(0, 4) + '.json', JSON.stringify(out, null, 1));
console.log('raw', raw.length, 'shows', parsed.list.length, 'small', small.length, 'skipped', parsed.skipped.length);
