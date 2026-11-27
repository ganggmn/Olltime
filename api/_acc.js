/* 서울시 혼잡 예보 적중률: 저장소(samples)에 5분마다 남긴 '그때의 예보'와 '나중의 실측' 단계를 맞대 봐요.
   rows: [{ ppl_time: 'YYYY-MM-DD HH:MM', lvl: '여유', fcst: [[기준 날짜 0시부터 분, 아래, 위, 단계], ...] }]
   같은 발표(ppl_time)의 같은 예보 시각은 한 번만 셉니다. 몇 시간 뒤 예보인지는 (예보 시각 − 발표 시각)을 시간으로 반올림. */
const NLV = l => (l === '붐빔' ? '혼잡' : l === '약간 붐빔' ? '약간 혼잡' : l);
const hm = s => +s.slice(11, 13) * 60 + +s.slice(14, 16);
const stamp = (base, m) => {
  const d = new Date(Date.parse(base + 'T00:00:00Z') + Math.floor(m / 1440) * 864e5).toISOString().slice(0, 10);
  const r = ((m % 1440) + 1440) % 1440;
  return `${d} ${String(Math.floor(r / 60)).padStart(2, '0')}:${String(r % 60).padStart(2, '0')}`;
};

export function forecastHits(rows, maxH = 12) {
  const act = new Map();
  for (const r of rows) if (r && r.ppl_time && r.lvl) act.set(r.ppl_time, NLV(r.lvl));
  const seen = new Set(), H = {};
  let first = null, last = null;
  for (const r of rows) {
    if (!r || !r.ppl_time || !Array.isArray(r.fcst)) continue;
    const base = r.ppl_time.slice(0, 10), p = hm(r.ppl_time);
    for (const f of r.fcst) {
      if (!Array.isArray(f) || !Number.isFinite(f[0])) continue;
      const h = Math.round((f[0] - p) / 60);
      if (h < 1 || h > maxH) continue;
      const tgt = stamp(base, f[0]), key = r.ppl_time + '|' + tgt;
      if (seen.has(key)) continue;
      seen.add(key);
      const a = act.get(tgt);
      if (!a) continue;
      const c = (H[h] = H[h] || [0, 0]);
      c[1]++;
      if (NLV(f[3]) === a) c[0]++;
      if (!first || r.ppl_time < first) first = r.ppl_time;
      if (!last || r.ppl_time > last) last = r.ppl_time;
    }
  }
  const horizon = Object.keys(H).map(Number).sort((a, b) => a - b).map(h => ({ h, n: H[h][1], level: Math.round((100 * H[h][0]) / H[h][1]) }));
  return { horizon, period: first ? [first, last] : null };
}
