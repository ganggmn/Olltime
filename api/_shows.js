/* 올림픽공원 누리집 '일정안내'(https://www.ksponco.or.kr/olympicpark/eventInfo/eventInfoList?mid=a20301010100)의 공연 일정을 읽어
   날짜별 시작 시각으로 풀어요. 누리집은 시각을 사람이 쓴 문장으로 줘요("금 오후 7시 / 토 오후 6시", "12.24(목) 8PM" 등).
   읽지 못한 것은 억지로 채우지 않고 skipped에 이유와 함께 남겨요. */
const SRC = 'https://www.ksponco.or.kr/olympicpark/eventInfo/eventInfoListAjax.es';
const W = '일월화수목금토', EN = { SUN: 0, MON: 1, TUE: 2, WED: 3, THU: 4, FRI: 5, SAT: 6 };
const pad = n => String(n).padStart(2, '0');
const norm = s => String(s ?? '').replace(/[！-～]/g, c => String.fromCharCode(c.charCodeAt(0) - 0xFEE0)).replace(/　/g, ' ').replace(/\s+/g, ' ').trim();

/* 큰 공연장 세 곳만 다뤄요(주차와 사람 흐름에 영향을 주는 곳). 나머지 공연장은 skipped로 */
export function venueOf(plc) {
  const p = norm(plc);
  if (/KSPO\s*DOME|체조경기장/i.test(p)) return 'KSPO DOME';
  if (/핸드볼|티켓링크\s*라이브\s*아레나/.test(p)) return '핸드볼경기장';
  if (/올림픽홀/.test(p)) return '올림픽홀';
  return null;
}
export const runOf = nd => { const m = norm(nd).match(/(\d{2,3})\s*분/); return m ? +m[1] : null; };
/* 목록에 쓸 짧은 이름: 연도와 꾸밈말을 떼고 '콘서트' 같은 말 앞까지 */
export function shortOf(title) {
  let s = norm(title).replace(/^\[[^\]]*\]\s*/, '').replace(/\b20\d{2}(-\d{2})?\b/g, ' ').replace(/\s+/g, ' ').trim();
  const cut = s.search(/\s*(단독|전국투어|팬콘서트|연말|\d+주년|콘서트|CONCERT|WORLD TOUR|LIVE TOUR|TOUR|LIVE|Special|Musical|FAN ?MEETING|팬미팅|[\[\(〈<:\-‘'"“])/i);
  if (cut > 0) s = s.slice(0, cut).trim();
  return s.replace(/\s*\([^)]*\)\s*$/, '').slice(0, 16) || norm(title).slice(0, 16);
}
export const cleanName = t => norm(t).replace(/^\[[^\]]*\]\s*/, '').replace(/\s+-\s+서울$| in seoul$/i, '').trim();

/* 맨 앞 갈래의 '시'는 문장 끝에서만 없어도 됨: 누리집 글이 '오후 5'에서 잘려 있는 경우가 있어요 */
const TIME = /(오전|오후)\s*(\d{1,2})\s*(?:시(?:\s*(\d{1,2})\s*분)?|$)|(\d{1,2})(?::(\d{2}))?(?::\d{2})?\s*(AM|PM)|(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분)?|(\d{1,2}):(\d{2})(?!\d)/gi;
const DATE = /(?:(\d{4})\s*[.년]\s*)?(\d{1,2})\s*[.월]\s*(\d{1,2})(?!\d)\s*일?/g;
const toMin = m => {
  let h, mi;
  if (m[1]) { h = +m[2]; mi = +(m[3] || 0); if (m[1] === '오후' && h < 12) h += 12; if (m[1] === '오전' && h === 12) h = 0; }
  else if (m[6]) { h = +m[4]; mi = +(m[5] || 0); const pm = /pm/i.test(m[6]); if (pm && h < 12) h += 12; if (!pm && h === 12) h = 0; }
  else if (m[7] != null) { h = +m[7]; mi = +(m[8] || 0); if (h >= 1 && h <= 9) h += 12; } /* '6시'처럼 오전·오후가 없으면 저녁으로 봄(공연 시각) */
  else { h = +m[9]; mi = +m[10]; }
  return h >= 0 && h < 24 && mi >= 0 && mi < 60 ? h * 60 + mi : null;
};
const refsIn = seg => {
  const dates = []; let rest = seg.replace(DATE, (_, y, mo, d) => { if (+mo >= 1 && +mo <= 12 && +d >= 1 && +d <= 31) { dates.push([+mo, +d]); return ' '; } return _; });
  if (dates.length) rest = rest.replace(/[~\-]\s*(\d{1,2})\s*일/g, (_, d) => { if (+d >= 1 && +d <= 31) { dates.push([dates[dates.length - 1][0], +d]); return ' '; } return _; });
  const wd = new Set(), bare = rest.replace(/\([^)]*\)/g, ' ');
  /* 날짜가 하나면 그 날짜를 따르고(옆의 요일은 덧붙인 말), 기간('14일 ~ 15일')처럼 여러 개가 적힌 뒤 괄호 밖에 요일이 있으면 요일을 따름 */
  if (dates.length === 1) return { dates };
  if (dates.length) rest = bare;
  if (/매일/.test(rest)) for (let i = 0; i < 7; i++) wd.add(i);
  if (/주말/.test(rest)) { wd.add(6); wd.add(0); }
  if (/평일/.test(rest)) for (let i = 1; i <= 5; i++) wd.add(i);
  rest = rest.replace(/주말|평일|매일|공휴일|요일/g, ' ');
  for (const m of rest.matchAll(/\b(SUN|MON|TUE|WED|THU|FRI|SAT)/gi)) wd.add(EN[m[1].toUpperCase()]);
  for (const m of rest.matchAll(/(?<![가-힣])([월화수목금토일](?:\s*[,·\/~]?\s*[월화수목금토일])*)(?![가-힣])/g)) for (const ch of m[1]) { const i = W.indexOf(ch); if (i >= 0) wd.add(i); }
  return wd.size ? { wd: [...wd] } : dates.length ? { dates } : null;
};
/* 문장 → 날짜별 시작 시각. 날짜가 적힌 것이 요일로 적힌 것보다 먼저, 날짜의 '월'이 틀리게 적혀 있으면 '일'만으로 맞춰요 */
export function timesOf(tm, begin, end) {
  const text = norm(tm), toks = []; let last = 0, prev = null;
  for (const m of text.matchAll(TIME)) {
    const min = toMin(m); if (min == null) continue;
    const seg = text.slice(last, m.index); last = m.index + m[0].length;
    const ref = refsIn(seg) || (/^[\s,·\/및와과]*$/.test(seg) ? prev : null); prev = ref;
    toks.push({ min, ref });
  }
  const byDate = new Map(), byWd = new Map(), plain = [];
  for (const t of toks) {
    if (!t.ref) plain.push(t.min);
    else if (t.ref.dates) for (const [mo, d] of t.ref.dates) { const k = mo + '-' + d; if (!byDate.has(k)) byDate.set(k, []); byDate.get(k).push(t.min); }
    else for (const w of t.ref.wd) { if (!byWd.has(w)) byWd.set(w, []); byWd.get(w).push(t.min); }
  }
  const out = [], miss = [], b = Date.parse(begin + 'T12:00:00+09:00'), e = Date.parse(end + 'T12:00:00+09:00');
  if (!isFinite(b) || !isFinite(e) || e < b) return { list: [], miss: ['기간을 읽지 못함'] };
  const days = []; for (let t = b; t <= e && days.length < 62; t += 864e5) days.push(new Date(t + 9 * 36e5));
  const inRange = new Set(days.map(x => (x.getUTCMonth() + 1) + '-' + x.getUTCDate()));
  const mentioned = new Set(); for (const m of text.matchAll(DATE)) if (+m[2] >= 1 && +m[2] <= 12) mentioned.add(+m[2] + '-' + +m[3]);
  const loose = new Map(); for (const [k, v] of byDate) if (!inRange.has(k)) { const d = k.split('-')[1]; if (!loose.has(d)) loose.set(d, v); }
  for (const x of days) {
    const d = x.toISOString().slice(0, 10), k = (x.getUTCMonth() + 1) + '-' + x.getUTCDate();
    let ts = byDate.get(k) || loose.get(String(x.getUTCDate()));
    if (!ts && !byDate.size) ts = byWd.get(x.getUTCDay()) || (byWd.size ? null : plain.length && days.length === 1 ? plain : plain.length === 1 ? plain : null);
    if (!ts && byDate.size && byWd.size) ts = byWd.get(x.getUTCDay());
    if (ts) for (const min of [...new Set(ts)].sort((p, q) => p - q)) out.push({ d, t: pad(Math.floor(min / 60)) + ':' + pad(min % 60) });
    /* 시각이 없는 날: 글에 날짜가 적혀 있으면 그 날짜만 '못 읽음'(나머지는 공연 없는 날), 요일로 적혀 있으면 적히지 않은 요일은 공연 없는 날,
       날짜도 요일도 없이 시각만 적혀 있는데 못 붙였으면 못 읽음 */
    else if (byDate.size || byWd.size) { if (mentioned.has(k)) miss.push(d); }
    else miss.push(d);
  }
  if (!out.length && !miss.length) miss.push(...days.map(x => x.toISOString().slice(0, 10)));
  return { list: out, miss };
}
/* 누리집 응답(한 달 치: [앞으로의 공연, 지난 공연]) 여러 개 → 공연 목록 */
export function parseShows(months) {
  const seen = new Set(), list = [], skipped = [];
  for (const mo of months) for (const g of (Array.isArray(mo) ? mo : [])) for (const it of (Array.isArray(g) ? g : [])) {
    if (!it || seen.has(it.evtSeq) || it.delYn === 'Y') continue; seen.add(it.evtSeq);
    const venue = venueOf(it.plc), name = cleanName(it.title);
    if (!venue) { skipped.push({ name, venue: norm(it.plc), why: '작은 공연장이라 다루지 않음' }); continue; }
    const r = timesOf(it.tm, it.beginDt, it.endDt);
    if (!r.list.length) { skipped.push({ name, venue, why: '시작 시각을 읽지 못함', text: norm(it.tm).slice(0, 80) }); continue; }
    if (r.miss.length) skipped.push({ name, venue, why: '일부 날짜의 시각을 읽지 못함', days: r.miss });
    const run = runOf(it.ndTm), short = shortOf(it.title);
    for (const x of r.list) list.push({ d: x.d, t: x.t, venue, name, short, run, seq: it.evtSeq });
  }
  list.sort((a, b) => a.d < b.d ? -1 : a.d > b.d ? 1 : a.t < b.t ? -1 : a.t > b.t ? 1 : a.venue < b.venue ? -1 : 1);
  return { list, skipped };
}
export const monthsFrom = (day, n) => { const y = +day.slice(0, 4), m = +day.slice(5, 7), out = []; for (let i = 0; i < n; i++) { const k = y * 12 + (m - 1) + i; out.push(String(Math.floor(k / 12)) + pad(k % 12 + 1)); } return out; };
/* 누리집에서 여러 달을 받아 옴. 한 달이라도 못 받으면 그 달은 비워 두고 failed에 적음 */
export async function fetchShows(yms, ms = 7000) {
  const got = await Promise.all(yms.map(async ym => {
    try {
      const r = await fetch(SRC, { method: 'POST', headers: { 'Content-Type': 'application/json;charset=UTF-8', Accept: 'application/json' }, body: JSON.stringify({ nowYM: ym, plcCd: '' }), signal: AbortSignal.timeout(ms) });
      if (!r.ok) return { ym, err: '서버 응답 ' + r.status };
      const j = await r.json(); if (!Array.isArray(j) || !Array.isArray(j[0])) return { ym, err: '형식이 다른 응답' };
      return { ym, j };
    } catch (e) { return { ym, err: e && e.name === 'TimeoutError' ? '응답 시간 초과' : '연결 실패' }; }
  }));
  const ok = got.filter(g => g.j), out = parseShows(ok.map(g => g.j));
  return { ...out, months: ok.map(g => g.ym), failed: got.filter(g => g.err).map(g => ({ month: g.ym, why: g.err })) };
}
