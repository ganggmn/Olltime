/* 서울시 실시간 도시데이터 응답을 사이트가 쓰는 작은 모양으로 줄여요. */
const list = v => (v == null || v === '' ? [] : Array.isArray(v) ? v : [v]);
const num = v => { const n = parseFloat(v); return Number.isFinite(n) ? n : null; };

/* '2026-11-23 01:30' -> 기준 날짜 0시부터 몇 분 (다음 날이면 1440을 넘어요) */
export function minutesFrom(ts, baseDate) {
  const [d, t] = String(ts).split(' ');
  const [h, m] = t.split(':').map(Number);
  const days = Math.round((Date.parse(d + 'T00:00:00Z') - Date.parse(baseDate + 'T00:00:00Z')) / 864e5);
  return days * 1440 + h * 60 + m;
}

export function compactCity(raw) {
  const c = raw && raw.CITYDATA;
  if (!c) {
    const r = (raw && (raw.RESULT || raw.result)) || {};
    throw new Error(`서울시 응답 ${r['RESULT.CODE'] || r.CODE || '?'} ${r['RESULT.MESSAGE'] || r.MESSAGE || ''}`.trim());
  }
  const p = list(c.LIVE_PPLTN_STTS)[0];
  if (!p || !p.PPLTN_TIME) throw new Error('인구 데이터가 비어 있어요');
  const base = p.PPLTN_TIME.slice(0, 10);
  const m = minutesFrom(p.PPLTN_TIME, base);
  const w = list(c.WEATHER_STTS)[0] || {};
  const now = {
    time: p.PPLTN_TIME, m, lvl: p.AREA_CONGEST_LVL,
    lo: num(p.AREA_PPLTN_MIN), hi: num(p.AREA_PPLTN_MAX), msg: p.AREA_CONGEST_MSG || '',
    nonres: num(p.NON_RESNT_PPLTN_RATE),
    /* 성별·나이 비율(%): 서울시 실시간 인구의 기지국 추정. 공연 관객 구성을 보려고 같이 남겨요 */
    demo: { male: num(p.MALE_PPLTN_RATE), female: num(p.FEMALE_PPLTN_RATE), age: [0, 10, 20, 30, 40, 50, 60, 70].map(k => num(p['PPLTN_RATE_' + k])), resnt: num(p.RESNT_PPLTN_RATE), nonres: num(p.NON_RESNT_PPLTN_RATE) },
    temp: num(w.TEMP), hum: num(w.HUMIDITY), wind: num(w.WIND_SPD),
    pcp: w.PCP_MSG || '', ptype: w.PRECPT_TYPE || '없음',
    pm10: num(w.PM10), pm25: num(w.PM25), air: w.AIR_IDX || ''
  };
  const fcst = list(p.FCST_PPLTN)
    .map(f => [minutesFrom(f.FCST_TIME, base), num(f.FCST_PPLTN_MIN), num(f.FCST_PPLTN_MAX), f.FCST_CONGEST_LVL])
    .filter(f => f[0] > m)
    .sort((a, b) => a[0] - b[0]);
  const road = (c.ROAD_TRAFFIC_STTS && c.ROAD_TRAFFIC_STTS.AVG_ROAD_DATA) || {};
  /* 그 구역의 대중교통·자전거·도로: 공연 날 사람이 어디로 빠지는지 보려고 같이 남겨요.
     버스·지하철은 [최소, 최대] 범위(오늘 누적, 최근 30·10·5분 승차·하차), 따릉이는 [대여소 번호, 세워진 자전거 수], 도로는 평균 속도 */
  const rng = (o, p, w, x) => { const lo = num(o[p + '_' + w + '_' + x + '_PPLTN_MIN']), hi = num(o[p + '_' + w + '_' + x + '_PPLTN_MAX']); return lo == null && hi == null ? null : [lo, hi]; };
  const flow = (o, p) => { if (!o || typeof o !== 'object') return null; const r = {}; let any = false; for (const w of ['ACML', '30WTHN', '10WTHN', '5WTHN']) for (const x of ['GTON', 'GTOFF']) { const v = rng(o, p, w, x); r[w.replace('WTHN', '') .toLowerCase() + '_' + (x === 'GTON' ? 'on' : 'off')] = v; if (v) any = true; } return any ? r : null; };
  const transit = {
    bus: flow(c.LIVE_BUS_PPLTN, 'BUS'), sub: flow(c.LIVE_SUB_PPLTN, 'SUB'),
    bike: list(c.SBIKE_STTS).map(b => [String(b.SBIKE_SPOT_ID || ''), num(b.SBIKE_PARKING_CNT)]).filter(b => b[0]),
    road: { idx: road.ROAD_TRAFFIC_IDX || '', spd: num(road.ROAD_TRAFFIC_SPD) }
  };
  return {
    now, fcst, transit,
    actual: [[m, now.lo, now.hi, now.lvl]],
    road: { idx: road.ROAD_TRAFFIC_IDX || '', spd: num(road.ROAD_TRAFFIC_SPD) },
    events: list(c.EVENT_STTS).map(e => ({ name: e.EVENT_NM, period: e.EVENT_PERIOD, place: (e.EVENT_PLACE || '').trim() })),
    lots: list(c.PRK_STTS).map(l => ({ name: l.PRK_NM, cap: num(l.CPCTY) }))
  };
}
