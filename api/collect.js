/* GET /api/collect: 실시간 인구와 주차 대수를 한 번 받아 저장소(Supabase)에 한 줄로 남겨요.
   사람이 여는 주소가 아니라 예약 작업이 5분마다 부르는 주소예요.
   필요한 환경변수: SEOUL_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY. COLLECT_TOKEN은 선택이에요.
   키와 토큰은 응답과 오류 메시지 어디에도 넣지 않아요. */
import { compactCity } from './_city.js';
import { ask } from './_subway.js';

/* 지하철 도착 정보는 공연이 있는 시간대(14:30~01:00)에만 모아요. 하루 호출 한도를 아끼려고 세 이름만 물어요. */
const SUBWAY_Q = ['올림픽공원', '올림픽공원(한국체대)', '한성백제'];

const AREA = '올림픽공원';
const PARKING_URL = 'https://www.ksponco.or.kr/online/main/parkingorsApi.do?apiKey=PARKING21803504';

async function city(key) {
  const url = `http://openapi.seoul.go.kr:8088/${encodeURIComponent(key)}/json/citydata/1/5/${encodeURIComponent(AREA)}`;
  const r = await fetch(url, { signal: AbortSignal.timeout(9000) });
  const text = (await r.text()).trim();
  if (text.startsWith('<') || !r.ok) throw new Error('서울시 응답 오류');
  const d = compactCity(JSON.parse(text));
  return { ...d.now, fcst: d.fcst };
}

async function parking() {
  const r = await fetch(PARKING_URL, { signal: AbortSignal.timeout(8000) });
  if (!r.ok) throw new Error('주차 응답 오류');
  let body = await r.json();
  if (Array.isArray(body)) body = body[0] || {};
  const sum = Number.parseInt(body.parking_sum, 10);
  if (String(body.code || body.resultCode || '0000') !== '0000' || !Number.isFinite(sum)) throw new Error('주차 값 없음');
  return sum;
}

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

  const [c, p] = await Promise.allSettled([city(SEOUL_KEY), parking()]);
  if (c.status !== 'fulfilled' && p.status !== 'fulfilled') return res.status(502).json({ ok: false, note: '두 값 모두 받지 못했어요' });

  const row = {
    ts: slot,
    parking: p.status === 'fulfilled' ? p.value : null,
    ppl_lo: c.status === 'fulfilled' ? c.value.lo : null,
    ppl_hi: c.status === 'fulfilled' ? c.value.hi : null,
    ppl_time: c.status === 'fulfilled' ? c.value.time : null,
    lvl: c.status === 'fulfilled' ? c.value.lvl : null,
    fcst: c.status === 'fulfilled' ? c.value.fcst : null
  };
  try {
    const r = await fetch(`${base}/rest/v1/samples?on_conflict=ts`, {
      method: 'POST',
      headers: { ...auth, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' },
      body: JSON.stringify(row), signal: AbortSignal.timeout(8000)
    });
    if (!r.ok) return res.status(502).json({ ok: false, note: `저장 실패 ${r.status}` });
    /* 지하철: 한국 시간 14:30~01:00에만 */
    let subway = null;
    const kstMin = (new Date(Date.now() + 9 * 3600e3).getUTCHours() * 60) + new Date().getUTCMinutes();
    if (SEOUL_SUBWAY_KEY && (kstMin >= 870 || kstMin < 60)) {
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
    return res.status(200).json({ ok: true, ts: slot, parking: row.parking !== null, people: row.ppl_lo !== null, subway });
  } catch (e) {
    return res.status(502).json({ ok: false, note: '저장소에 닿지 못했어요' });
  }
}
