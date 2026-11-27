// 실시간(2026-11-22~27) 검증 묶음: vs_seoul.mjs와 같은 조건에 '현재값 유지'와 혼잡 단계, 주차 2시간 앞을 더함.
//  사람 수: 대상 시각 T(서울시 측정, 정시)보다 L분 앞서 손에 있던 정보만 씀
//   - 서울시 공식 예측: 받은 시각 ≤ T − L 인 응답 중 가장 늦은 것의 T 예측(범위 가운데, 단계)
//   - 올타임(지금 사이트 model_main.js): 받은 시각 T+30을 L+30분 앞서 낸 예상
//   - 현재값 유지: 받은 시각 ≤ T − L 인 마지막 측정 값(범위 가운데). 서울시 값은 측정 30분 뒤에 들어오므로 측정 시각 ≤ T − L − 30
//   정답: 서울시가 나중에 준 T 측정 값(범위 가운데)과 단계
//  주차: 사이트 그대로 2시간 앞 예상(carPast) vs 실측 parking_sum, 현재값 유지 = 2시간 전 실측
// 사용: 맥 data 폴더에서 node ../analysis/sim/live_eval.mjs → ~/bt/live_eval.json
import fs from 'fs'; import os from 'os';
const H = os.homedir(), DD = H + '/mnt/(주)한국체육산업개발 공모전/data/', SIM = H + '/mnt/(주)한국체육산업개발 공모전/analysis/sim/';
const csv = f => fs.readFileSync(DD + f, 'utf8').replace(/^﻿/, '').trim().split('\n').slice(1).map(l => l.split(','));
const P = csv('citydata/ppltn.csv'), F = csv('citydata/fcst.csv'), K = csv('parking/parking.csv');
const tmin = s => new Date(s.slice(0, 16).replace(' ', 'T') + ':00+09:00').getTime() / 60000;
const dayOf = s => s.slice(0, 10), mm = s => +s.slice(11, 13) * 60 + +s.slice(14, 16);
const patch = s => s.replace('if(pmode){slots.forEach(m=>{if(m<=lastP.m){const e0=before(pe,m-AHEAD)', 'if(pmode){const AH=o.ahead||AHEAD;(o.pslots||slots).forEach(m=>{if(m<=lastP.m){const e0=before(pe,m-AH)');
globalThis.OLL = undefined; new Function(fs.readFileSync(SIM + 'gp.js', 'utf8'))(); const src = patch(fs.readFileSync(SIM + 'model_main.js', 'utf8')); if (!src.includes('o.pslots')) throw 'patch'; new Function(src)(); const O = globalThis.OLL;
const days = ['2026-11-22', '2026-11-23', '2026-11-24', '2026-11-25', '2026-11-26', '2026-11-27'];
const park = new Map(K.filter(r => r[1] !== '').map(r => [r[0].slice(0, 15) + '0', +r[1]]));
const truth = new Map(); for (const r of P) { const k = r[1]; if (!truth.has(k)) truth.set(k, [(+r[3] + +r[4]) / 2, +r[3], +r[4], r[2]]); }
const meas = [...truth.entries()].map(([k, v]) => [tmin(k), v[0]]).sort((a, b) => a[0] - b[0]);
const LIST = {};
for (const d of days) { const rows = P.filter(r => dayOf(r[0]) === d).map(r => { const m = Math.floor(mm(r[0]) / 5) * 5, pk = park.get(r[0].slice(0, 15) + '0'); return [m, pk == null ? null : pk, +r[3], +r[4], r[2], Math.round(tmin(r[1]) - tmin(d + ' 00:00'))]; });
  const seen = new Set(); LIST[d] = rows.filter(r => !seen.has(r[0]) && seen.add(r[0])); }
const ps = []; for (let m = 0; m < 1440; m += 5) ps.push(m);
const byT = new Map(); for (const r of F) { const k = r[2]; if (!byT.has(k)) byT.set(k, []); byT.get(k).push([tmin(r[0]), (+r[4] + +r[5]) / 2, r[3]]); }
const lv = {}; for (const r of P) { const L = r[2]; (lv[L] = lv[L] || [9e9, 0]); lv[L][0] = Math.min(lv[L][0], +r[3]); lv[L][1] = Math.max(lv[L][1], +r[4]); }
const out = { levels: lv, ppl: [], car: [] };
for (const L of [60, 90, 150]) for (const d of days) {
  const R = new Map(O.run(LIST[d], { day: d, isToday: false, ahead: L + 30, pslots: ps }).pPast.map(p => [p.m, p.v]));
  for (let h = 7; h <= 23; h++) { const T = `${d} ${String(h).padStart(2, '0')}:00`, tr = truth.get(T); if (!tr) continue;
    const t0 = tmin(T), cand = (byT.get(T) || []).filter(x => x[0] <= t0 - L).sort((a, b) => b[0] - a[0])[0], a = R.get(h * 60 + 30);
    const pv = meas.filter(x => x[0] <= t0 - L - 30).pop(); if (!cand || a == null || !pv) continue;
    out.ppl.push({ L, d, h, truth: tr[0], lo: tr[1], hi: tr[2], lvl: tr[3], seoul: cand[1], seoulLvl: cand[2], main: a, pers: pv[1], persAge: t0 - pv[0] }); } }
// 혼잡 경보용: 5분마다(07~23시) 2시간 앞(L=90) 사람 수 예상, 현재값 유지(값·단계)
out.ppl5 = []; const lvAt = new Map([...truth.entries()].map(([k, v]) => [tmin(k), v[3]]));
for (const d of days) { const R = new Map(O.run(LIST[d], { day: d, isToday: false, ahead: 120, pslots: ps }).pPast.map(p => [p.m, p.v]));
  for (const [k, tr] of truth) { if (dayOf(k) !== d) continue; const t0 = tmin(k), mT = mm(k); if (mT < 420 || mT > 1380) continue; const a = R.get(mT + 30);
    const pv = meas.filter(x => x[0] <= t0 - 120).pop(); if (a == null || !pv) continue;
    out.ppl5.push({ d, m: mT, truth: tr[0], lvl: tr[3], main: a, pers: pv[1], persLvl: lvAt.get(pv[0]) }); } }
for (const d of days) { const R = O.run(LIST[d], { day: d, isToday: false });
  for (const p of R.carPast) { const a = R.carMap.get(p.m), b = R.carMap.get(p.m - 120); if (a == null || b == null || p.m < 420 || p.m > 1380) continue; out.car.push({ d, m: p.m, show: R.isShow, k: R.k, truth: a, main: p.v, pers: b }); } }
fs.writeFileSync(H + '/bt/live_eval.json', JSON.stringify(out));
const mae = (A, k) => A.reduce((s, r) => s + Math.abs(r[k] - r.truth), 0) / A.length;
console.log('levels', JSON.stringify(lv));
for (const L of [60, 90, 150]) { const A = out.ppl.filter(r => r.L === L); console.log(`ppl L${L} n=${A.length} MAE main ${mae(A, 'main').toFixed(0)} seoul ${mae(A, 'seoul').toFixed(0)} pers ${mae(A, 'pers').toFixed(0)}`); }
for (const s of [true, false]) { const A = out.car.filter(r => r.show === s); console.log(`car show=${s} n=${A.length} days=${[...new Set(A.map(r => r.d))]} MAE main ${mae(A, 'main').toFixed(0)} pers ${mae(A, 'pers').toFixed(0)}`); }
