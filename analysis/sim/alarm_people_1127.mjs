// 11/27 실측(서울시 5분 + 주차 5분)으로 '끝난 뒤 사람 수 감소'를 출차 알림에 맞춰 옮기면 어떤지 다시 돌려 봄(사후).
// 사용: node analysis/sim/alarm_people_1127.mjs <trend 파일(/api/trend?day=2026-11-27 의 list를 ;과 ,로 이은 것)> <main의 model.js>
// 새 방식: 기준 시각이 알림(21:30, 새 규칙) 뒤면 예상 끝 E = 알림 − L분(L=20: 2025 '알림 − 출차 몰림 시작' 중앙값 + 11/22로 정한 감소 모양, 사전 근거)
import fs from 'fs';
const [trendF, mainF] = process.argv.slice(2);
const list = fs.readFileSync(trendF, 'utf8').trim().split(';').map(r => r.split(',').map((v, i) => i === 4 ? (v || null) : (v === '' ? null : +v)));
const patch = (s, isNew) => {
  s = s.replace('if(pmode){slots.forEach(m=>{if(m<=lastP.m){const e0=before(pe,m-AHEAD)', 'if(pmode){const AH=o.ahead||AHEAD;(o.pslots||slots).forEach(m=>{if(m<=lastP.m){const e0=before(pe,m-AH)');
  if (isNew) s = s.replace('const E=pa?ev[1]+(ev[2]?ev[2]+POST.lag:POST.onset):null;', 'const E00=pa?ev[1]+(ev[2]?ev[2]+POST.lag:POST.onset):null,Eof=iss=>(pa&&o.alarm!=null&&iss>=o.alarm)?o.alarm-(o.alarmLead==null?20:o.alarmLead):E00;')
    .replace('const fcCell=(m,e0)=>{const f=', 'const fcCell=(m,e0)=>{const E=Eof(e0.m);const f=');
  return s;
};
const load = (src, isNew) => { globalThis.OLL = undefined; new Function(fs.readFileSync(new URL('../../gp.js', import.meta.url), 'utf8'))(); new Function(patch(fs.readFileSync(src, 'utf8'), isNew))(); return globalThis.OLL; };
const MAIN = load(mainF, false), NEW = load(new URL('../../model.js', import.meta.url), true);
const pslots = []; for (let m = 0; m < 1440; m += 5) pslots.push(m);
const V = { '지금 사이트': [MAIN, {}], '새(적힌 끝+45)': [NEW, {}], '새+알림 L20(사전 근거)': [NEW, { alarm: 1290, alarmLead: 20 }], '새+알림 L10': [NEW, { alarm: 1290, alarmLead: 10 }], '새+알림 L5(11/27 근거)': [NEW, { alarm: 1290, alarmLead: 5 }], '새+알림 L0': [NEW, { alarm: 1290, alarmLead: 0 }] };
const W = { '18~21시': [1080, 1255], '21~24시': [1260, 1435], '18~24시': [1080, 1435] };
for (const ah of [120, 60, 30]) { console.log('---', ah + '분 앞'); for (const [nm, [O, opt]] of Object.entries(V)) { const R = O.run(list, { day: '2026-11-27', isToday: false, ahead: ah, pslots, ...opt });
  const est = new Map(R.pe.map(p => [p.m, p.v])), f = new Map(R.pPast.map(p => [p.m, p.v]));
  console.log(nm.padEnd(20), Object.entries(W).map(([w, [a, b]]) => { let e = 0, t = 0; for (const [m, v] of est) { if (m < a || m > b || !f.has(m)) continue; e += Math.abs(f.get(m) - v); t += v; } return w + ' ' + (100 * (1 - e / t)).toFixed(1); }).join(' | ')); } }
