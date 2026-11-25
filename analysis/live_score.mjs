/* 누구나 같은 채점을 다시 해 보는 스크립트(Node 20 이상, 설치할 것 없음).
   공개된 기록(https://olltime.vercel.app/api/trend?day=날짜)을 받아, 저장소의 model.js로 '2시간 앞서 낸 예상'을 채점해요.
   사용: node analysis/live_score.mjs 2026-11-23 2026-11-24 [--win 10 --dn 2000 --dp 20.0 --k 3.0]
   같은 날짜와 같은 기준이면 /api/score 와 같은 숫자가 나와야 해요. */
import '../gp.js';
import '../model.js';
const OLL = globalThis.OLL;
export async function scoreFrom(fetchDay, days, rules) {
  const byDay = {};
  for (const d of days) { const j = await fetchDay(d); if (j && j.ok && j.list.length) byDay[d] = j.list; }
  return OLL.scoreDays(byDay, OLL.cleanRules(rules || {}));
}
export function say(out) {
  const L = [], f = (s, u) => s.n ? `${s.n}번, 평균 ${s.mae}${u}(${s.pct}%) 차이` : '채점할 값 없음';
  const r = out.rules, on = [r.win && (r.dn || r.dp) ? `${r.win}분 사이 사람 수가 ${[r.dn ? r.dn + '명' : '', r.dp ? r.dp + '%' : ''].filter(Boolean).join(' 또는 ')} 넘게 변함` : '', r.k ? `예상이 평소 오차의 ${r.k}배 넘게 빗나감` : ''].filter(Boolean);
  L.push(on.length ? `이상 징후 기준: ${on.join(', ')}` : '이상 징후 기준: 정하지 않음(모든 시간을 그대로 채점)');
  L.push(`평소 오차(모든 날의 가운데값): 주차 ${out.usual.car ?? '-'}대, 사람 수 ${out.usual.ppl ?? '-'}명`);
  for (const d of out.days) {
    L.push(`\n${d.day}`);
    L.push(`  주차 2시간 앞 예상: ${f(d.car, '대')}` + (d.events.length ? ` / 이상 징후 시간을 빼면 ${f(d.carEx, '대')}` : ''));
    L.push(`  사람 수 2시간 앞 예상: ${f(d.ppl, '명')}` + (d.ppl.n ? `, 서울시 범위 안 ${d.ppl.inband}%` : '') + (d.events.length ? ` / 빼면 ${f(d.pplEx, '명')}` : ''));
    for (const e of d.events) L.push(`  알림: ${e.text}`);
  }
  L.push(`\n합계  주차: ${f(out.total.car, '대')} / 이상 징후 제외 ${f(out.total.carEx, '대')}`);
  L.push(`      사람 수: ${f(out.total.ppl, '명')} / 이상 징후 제외 ${f(out.total.pplEx, '명')}`);
  return L.join('\n');
}
if (process.argv[1] && process.argv[1].endsWith('live_score.mjs')) {
  const args = process.argv.slice(2), days = args.filter(a => /^\d{4}-\d{2}-\d{2}$/.test(a)), rules = {};
  for (let i = 0; i < args.length; i++) if (args[i].startsWith('--')) rules[args[i].slice(2)] = args[i + 1];
  if (!days.length) { console.log('날짜를 하나 이상 주세요. 예: node analysis/live_score.mjs 2026-11-24'); process.exit(1); }
  const site = process.env.OLLTIME_SITE || 'https://olltime.vercel.app';
  const out = await scoreFrom(async d => (await fetch(`${site}/api/trend?day=${d}`)).json(), days, rules);
  console.log(say(out));
}
