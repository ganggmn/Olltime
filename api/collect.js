/* GET /api/collect: 실시간 인구와 주차 대수를 한 번 받아 저장소(Supabase)에 한 줄로 남겨요.
   사람이 여는 주소가 아니라 예약 작업이 5분마다 부르는 주소예요.
   필요한 환경변수: SEOUL_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY. COLLECT_TOKEN은 선택이에요.
   저장한 뒤 그 칸에 사이트가 내는 예상도 forecast_log에 남겨요(analysis/forecast_log.sql).
   키와 토큰은 응답과 오류 메시지 어디에도 넣지 않아요. */
import { compactCity } from './_city.js';
import { ask } from './_subway.js';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import '../gp.js';
import '../model.js';

/* 지하철 도착 정보: 공원 둘레의 세 역을 하루 종일 모아요(서울시 호출 한도가 풀림, 2026년 11월 26일부터).
   몽촌토성역은 서울시에 '몽촌토성(평화의문)'으로 올라 있어요('몽촌토성'만 물으면 빈 목록, 2026년 11월 26일 확인). */
const SUBWAY_Q = ['올림픽공원', '올림픽공원(한국체대)', '한성백제', '몽촌토성(평화의문)'];

const AREA = '올림픽공원';
/* 공원 둘레: 서울시 '잠실 관광특구' 구역(2.31㎢)은 '올림픽공원' 구역(1.45㎢)을 통째로 품고 있어요.
   두 값의 차이가 공원 서쪽 테두리(잠실·방이동 쪽, 약 0.86㎢)의 사람 수예요. 2026년 11월 26일부터 모아요. */
const RIM = ['잠실 관광특구'];
const PARKING_URL = 'https://www.ksponco.or.kr/online/main/parkingorsApi.do?apiKey=PARKING21803504';

async function city(key, area = AREA) {
  const url = `http://openapi.seoul.go.kr:8088/${encodeURIComponent(key)}/json/citydata/1/5/${encodeURIComponent(area)}`;
  const r = await fetch(url, { signal: AbortSignal.timeout(9000) });
  const text = (await r.text()).trim();
  if (!r.ok) throw new Error(`서버 응답 ${r.status}`);
  if (text.startsWith('<')) throw new Error('형식이 다른 응답');
  const d = compactCity(JSON.parse(text));
  return { ...d.now, fcst: d.fcst, transit: d.transit };
}

async function parking() {
  const r = await fetch(PARKING_URL, { signal: AbortSignal.timeout(8000) });
  if (!r.ok) throw new Error(`서버 응답 ${r.status}`);
  let body = await r.json();
  if (Array.isArray(body)) body = body[0] || {};
  const sum = Number.parseInt(body.parking_sum, 10);
  if (String(body.code || body.resultCode || '0000') !== '0000' || !Number.isFinite(sum)) throw new Error('값이 비어 있음');
  return sum;
}

/* 예측 기록: 이 5분 칸에 사이트가 내는 예상을 '그때 낸 값' 그대로 남겨요(나중에 다시 계산한 값이 아님).
   저장소의 forecast_log 표는 고치기·지우기·비우기를 막아 두었고, 기록 시각(저장소 시계)과 앞 줄 지문(sha256 사슬)은 저장소가 직접 붙여요.
   자리값: 지금 사이트의 model.js·gp.js 지문과 배포 커밋. 출차 혼잡 시작 알림은 11/28 전에 고정한 규칙(N2: 10분 감소 78대 두 번 연속)의 상태예요. */
const fileSha = () => { try { const h = createHash('sha256'); for (const f of ['../model.js', '../gp.js']) h.update(readFileSync(new URL(f, import.meta.url))); return h.digest('hex'); } catch (e) { return 'fn:' + createHash('sha256').update(String(globalThis.OLL.run)).digest('hex'); } };
const MODEL_SHA = fileSha();
const n2Fire = (P, st, run) => { const e0 = st + Math.max(60, run - 45), Q = P.filter(r => r[0] >= st && r[1] != null); let c = 0; for (const [m, v] of Q) { const pv = Q.find(r => r[0] >= m - 12 && r[0] <= m - 8), hit = !!pv && pv[1] - v >= 78; if (m < e0) { c = 0; continue; } c = hit ? c + 1 : 0; if (c >= 2) return m; } return null; };
async function logForecast(base, auth, slot) {
  const OLL = globalThis.OLL, kst = new Date(Date.parse(slot) + 9 * 3600e3), day = kst.toISOString().slice(0, 10);
  const from = new Date(`${day}T00:00:00+09:00`).toISOString(), to = new Date(Date.parse(from) + 864e5).toISOString();
  const r = await fetch(`${base}/rest/v1/samples?select=ts,parking,ppl_lo,ppl_hi,lvl&ts=gte.${encodeURIComponent(from)}&ts=lt.${encodeURIComponent(to)}&order=ts.asc&limit=400`, { headers: auth, signal: AbortSignal.timeout(6000) });
  if (!r.ok) return `읽기 실패 ${r.status}`;
  const list = (await r.json()).map(x => [Math.round((Date.parse(x.ts) - Date.parse(from)) / 60000), x.parking, x.ppl_lo, x.ppl_hi, x.lvl]);
  if (!list.length) return '오늘 기록 없음';
  const R = OLL.run(list, { day, isToday: true }), rd = v => (v == null ? null : Math.round(v));
  const ks = (OLL.EVT[day] || []).find(e => e[0] === 'KSPO DOME');
  const payload = {
    m: list[list.length - 1][0], k: R.k, show: R.isShow, shows: OLL.EVT[day] || [],
    car: { now: R.car.length ? R.car[R.car.length - 1].v : null, fut: R.carFut.map(p => [p.m, rd(p.v)]) },
    ppl: { now: R.pe.length ? rd(R.pe[R.pe.length - 1].v) : null, fut: R.pFut.map(p => [p.m, rd(p.v)]) },
    exit_n2: ks ? { st: ks[1], run: ks[2] || 150, fire: n2Fire(list.map(x => [x[0], x[1]]), ks[1], ks[2] || 150) } : null
  };
  const w = await fetch(`${base}/rest/v1/forecast_log`, {
    method: 'POST', headers: { ...auth, 'Content-Type': 'application/json', Prefer: 'return=minimal' },
    body: JSON.stringify({ slot_ts: slot, day, model_sha: MODEL_SHA, commit_sha: process.env.VERCEL_GIT_COMMIT_SHA || null, payload }), signal: AbortSignal.timeout(6000)
  });
  return w.ok ? 'ok' : `저장 실패 ${w.status}`;
}

/* 실패한 이유를 짧은 말로: 키나 주소는 넣지 않아요 */
const why = e => (e && (e.name === 'TimeoutError' || e.name === 'AbortError') ? '응답 시간 초과' : e && /^(서버 응답 \d+|형식이 다른 응답|값이 비어 있음)$/.test(e.message) ? e.message : e instanceof SyntaxError ? '형식이 다른 응답' : '연결 실패');

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  const { SEOUL_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, COLLECT_TOKEN, SEOUL_SUBWAY_KEY } = process.env;
  if (!SEOUL_KEY || !SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
    return res.status(503).json({ ok: false, note: '저장소가 아직 연결되지 않았어요' });
  }
  /* 토큰을 정해 두었으면 토큰이 맞을 때만 받아요. 없으면 아래의 "5분에 한 번" 제한만으로 지켜요. */
  if (COLLECT_TOKEN && req.headers['x-collect-token'] !== COLLECT_TOKEN) return res.status(401).json({ ok: false });
  const base = SUPABASE_URL.replace(/\/$/, '');
  const auth = { apikey: SUPABASE_SERVICE_KEY, Authorization: `Bearer ${SUPABASE_SERVICE_KEY}` };
  const slot = new Date(Math.floor(Date.now() / 300000) * 300000).toISOString();
  /* 이번 5분 칸이 이미 채워졌으면 서울시와 기관을 다시 부르지 않아요. 누가 이 주소를 여러 번 불러도 호출 수가 늘지 않아요. */
  try {
    const r0 = await fetch(`${base}/rest/v1/samples?select=ts,parking,ppl_lo&order=ts.desc&limit=1`, { headers: auth, signal: AbortSignal.timeout(6000) });
    if (!r0.ok) return res.status(502).json({ ok: false, note: `저장소 읽기 실패 ${r0.status}` });
    const last = (await r0.json())[0];
    if (last && new Date(last.ts).toISOString() === slot && last.parking !== null && last.ppl_lo !== null) {
      return res.status(200).json({ ok: true, ts: slot, skipped: true });
    }
  } catch (e) {
    return res.status(502).json({ ok: false, note: '저장소에 닿지 못했어요' });
  }

  let [c, p, rim] = await Promise.allSettled([city(SEOUL_KEY), parking(), Promise.allSettled(RIM.map(a => city(SEOUL_KEY, a)))]);
  /* 못 받은 것만 한 번 더 받아요. 11/26~28 서버 기록의 실패 7번(서울시 정각 '형식이 다른 응답' 3번, 기관 주차 '응답 시간 초과' 4번)은
     맥 수집기가 같은 분에 18~19초 늦게 부른 값으로는 모두 받아졌어요. 그래서 잠깐(기본 10초) 기다렸다 다시 불러요. */
  if (c.status !== 'fulfilled' || p.status !== 'fulfilled') {
    const wait = process.env.COLLECT_RETRY_MS != null ? +process.env.COLLECT_RETRY_MS : 10000;
    await new Promise(r => setTimeout(r, wait));
    const [c2, p2] = await Promise.allSettled([c.status === 'fulfilled' ? Promise.resolve(c.value) : city(SEOUL_KEY), p.status === 'fulfilled' ? Promise.resolve(p.value) : parking()]);
    c = c2; p = p2;
  }
  /* 하나라도 못 받았으면 이유를 수집 기록(collect_log)에 남겨요. 알림판이 '오류'와 '미확인'을 가르는 데 써요. */
  if (c.status !== 'fulfilled' || p.status !== 'fulfilled') {
    try {
      await fetch(`${base}/rest/v1/collect_log?on_conflict=ts`, {
        method: 'POST', headers: { ...auth, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' },
        body: JSON.stringify({ ts: slot, city: c.status === 'fulfilled' ? 'ok' : why(c.reason), parking: p.status === 'fulfilled' ? 'ok' : why(p.reason) }), signal: AbortSignal.timeout(6000)
      });
    } catch (e) { /* 기록을 못 남겨도 수집은 계속해요 */ }
  }
  if (c.status !== 'fulfilled' && p.status !== 'fulfilled') return res.status(502).json({ ok: false, note: '두 값 모두 받지 못했어요' });

  const row = {
    ts: slot,
    parking: p.status === 'fulfilled' ? p.value : null,
    ppl_lo: c.status === 'fulfilled' ? c.value.lo : null,
    ppl_hi: c.status === 'fulfilled' ? c.value.hi : null,
    ppl_time: c.status === 'fulfilled' ? c.value.time : null,
    lvl: c.status === 'fulfilled' ? c.value.lvl : null,
    fcst: c.status === 'fulfilled' ? c.value.fcst : null,
    demo: c.status === 'fulfilled' ? c.value.demo : null,
    transit: c.status === 'fulfilled' ? c.value.transit : null
  };
  try {
    const r = await fetch(`${base}/rest/v1/samples?on_conflict=ts`, {
      method: 'POST',
      headers: { ...auth, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' },
      body: JSON.stringify(row), signal: AbortSignal.timeout(8000)
    });
    if (!r.ok) return res.status(502).json({ ok: false, note: `저장 실패 ${r.status}` });
    /* 공원 둘레 구역: 못 받은 구역도 이유와 함께 한 줄 남겨요 */
    const rimRows = (rim.status === 'fulfilled' ? rim.value : []).map((g, i) => (g.status === 'fulfilled'
      ? { ts: slot, area: RIM[i], lo: g.value.lo, hi: g.value.hi, ppl_time: g.value.time, lvl: g.value.lvl, fcst: g.value.fcst, demo: g.value.demo, transit: g.value.transit, err: null }
      : { ts: slot, area: RIM[i], lo: null, hi: null, ppl_time: null, lvl: null, fcst: null, demo: null, transit: null, err: why(g.reason) }));
    const rimSave = rimRows.length ? fetch(`${base}/rest/v1/area_samples?on_conflict=ts,area`, {
      method: 'POST', headers: { ...auth, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' },
      body: JSON.stringify(rimRows), signal: AbortSignal.timeout(8000)
    }).then(r => (r.ok ? rimRows.filter(x => x.err === null).length : `저장 실패 ${r.status}`)).catch(() => '저장소에 닿지 못함') : Promise.resolve(0);
    /* 지하철: 하루 종일 */
    let subway = null;
    if (SEOUL_SUBWAY_KEY) {
      const got = await Promise.allSettled(SUBWAY_Q.map(q => ask(SEOUL_SUBWAY_KEY, q)));
      const list = got.flatMap(g => (g.status === 'fulfilled' ? g.value : []));
      if (got.some(g => g.status === 'fulfilled')) {
        const r2 = await fetch(`${base}/rest/v1/subway_samples?on_conflict=ts`, {
          method: 'POST',
          headers: { ...auth, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' },
          body: JSON.stringify({ ts: slot, list }), signal: AbortSignal.timeout(8000)
        });
        subway = r2.ok ? list.length : `저장 실패 ${r2.status}`;
      }
    }
    const areas = await rimSave;
    let forecast;
    try { forecast = await logForecast(base, auth, slot); } catch (e) { forecast = '기록 실패'; }
    return res.status(200).json({ ok: true, ts: slot, parking: row.parking !== null, people: row.ppl_lo !== null, areas, subway, forecast });
  } catch (e) {
    return res.status(502).json({ ok: false, note: '저장소에 닿지 못했어요' });
  }
}
