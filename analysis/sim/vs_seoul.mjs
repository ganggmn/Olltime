// 서울시 공식 예측(실시간 도시데이터 FCST_PPLTN)과 올타임 예상(지금 사이트·새 방식)을 같은 조건으로 견줌.
// 같은 조건: 대상 시각 T(서울시 측정 시각, 정시)보다 L분 앞서 손에 있던 정보만 씀.
//  - 서울시: 받은 시각 ≤ T − L 인 응답 중 가장 늦은 것의 T 예측(범위 가운데)
//  - 올타임: 받은 시각 m = T+30 인 값을 A = L+30분 앞서 낸 예상(사이트와 같은 계산)
// 정답: 서울시가 나중에 준 T 측정 값(범위 가운데). 자료: 맥 수집기 citydata/ppltn.csv, fcst.csv(2026-11-22 05:35~)
import fs from 'fs'; import os from 'os';
const H = os.homedir(), DD = H + '/mnt/(주)한국체육산업개발 공모전/data/', SIM = H + '/mnt/(주)한국체육산업개발 공모전/analysis/sim/';
const csv = f => fs.readFileSync(DD + f, 'utf8').replace(/^﻿/, '').trim().split('\n').slice(1).map(l => l.split(','));
const P = csv('citydata/ppltn.csv'), F = csv('citydata/fcst.csv'), K = csv('parking/parking.csv');
const tmin = s => new Date(s.slice(0, 16).replace(' ', 'T') + ':00+09:00').getTime() / 60000;
const dayOf = s => s.slice(0, 10), mm = s => +s.slice(11, 13) * 60 + +s.slice(14, 16);
const patch = (s, isNew) => s.replace('if(pmode){slots.forEach(m=>{if(m<=lastP.m){const e0=before(pe,m-AHEAD)', 'if(pmode){const AH=o.ahead||AHEAD;(o.pslots||slots).forEach(m=>{if(m<=lastP.m){const e0=before(pe,m-AH)');
const load = (f, isNew) => { globalThis.OLL = undefined; new Function(fs.readFileSync(SIM + 'gp.js', 'utf8'))(); const s = patch(fs.readFileSync(SIM + f, 'utf8')); if (!s.includes('o.pslots')) throw 'patch'; new Function(s)(); return globalThis.OLL; };
const M = { main: load('model_main.js'), new: load('model_new.js') };
// 날마다 사이트와 같은 줄 [받은 분(5분), 주차, 아래, 위, 단계, 측정 분]
const days = [...new Set(P.map(r => dayOf(r[0])))].filter(d => d >= '2026-11-22' && d <= '2026-11-27');
const park = new Map(K.map(r => [r[0].slice(0, 16), +r[1]]));
const truth = new Map(); for (const r of P) { const k = r[1]; if (!truth.has(k)) truth.set(k, [(+r[3] + +r[4]) / 2, +r[3], +r[4]]); }
const LIST = {};
for (const d of days) { const rows = P.filter(r => dayOf(r[0]) === d).map(r => { const m = Math.floor(mm(r[0]) / 5) * 5, pk = park.get(r[0].slice(0, 15) + '0'); return [m, pk == null ? null : pk, +r[3], +r[4], r[2], Math.round(tmin(r[1]) - tmin(d + ' 00:00'))]; });
  const seen = new Set(); LIST[d] = rows.filter(r => !seen.has(r[0]) && seen.add(r[0])); }
const ps = []; for (let m = 0; m < 1440; m += 5) ps.push(m);
// 서울시 예측 찾기
const byT = new Map(); for (const r of F) { const k = r[2]; if (!byT.has(k)) byT.set(k, []); byT.get(k).push([tmin(r[0]), (+r[4] + +r[5]) / 2, +r[4], +r[5]]); }
const out = [];
for (const L of [60, 90, 150]) for (const d of days) {
  const R = {}; for (const [nm, O] of Object.entries(M)) R[nm] = new Map(O.run(LIST[d], { day: d, isToday: false, ahead: L + 30, pslots: ps }).pPast.map(p => [p.m, p.v]));
  for (let h = 7; h <= 23; h++) { const T = `${d} ${String(h).padStart(2, '0')}:00`, tr = truth.get(T); if (!tr) continue;
    const cand = (byT.get(T) || []).filter(x => x[0] <= tmin(T) - L).sort((a, b) => b[0] - a[0])[0];
    const m = h * 60 + 30, a = R.main.get(m), b = R.new.get(m); if (!cand || a == null || b == null) continue;
    out.push({ L, d, h, truth: tr[0], lo: tr[1], hi: tr[2], seoul: cand[1], main: a, new: b, issuedSeoulMinBefore: Math.round(tmin(T) - cand[0]) }); } }
fs.writeFileSync(H + '/bt/vs_seoul.json', JSON.stringify(out));
const SH = { '2026-11-22': [17, 22], '2026-11-27': [19, 24] };
const sum = (rows, k) => { const e = rows.reduce((s, r) => s + Math.abs(r[k] - r.truth), 0), t = rows.reduce((s, r) => s + r.truth, 0), inb = rows.filter(r => r[k] >= r.lo && r[k] <= r.hi).length; return `${(100 * (1 - e / t)).toFixed(1)}%(${Math.round(e / rows.length)}명, 칸안 ${Math.round(100 * inb / rows.length)}%)`; };
for (const L of [60, 90, 150]) { const A = out.filter(r => r.L === L), S = A.filter(r => SH[r.d] && r.h >= SH[r.d][0] && r.h <= SH[r.d][1]), N = A.filter(r => !SH[r.d]);
  console.log(`--- ${L}분 앞 (n=${A.length}, 공연 저녁 ${S.length}, 공연 없는 날 ${N.length})`);
  for (const [lab, rows] of [['전체', A], ['공연 저녁', S], ['공연 없는 날', N]]) console.log(`  ${lab.padEnd(8)} 서울시 ${sum(rows, 'seoul')} | 지금 사이트 ${sum(rows, 'main')} | 새 방식 ${sum(rows, 'new')} | 새가 서울시보다 가까운 시각 ${rows.filter(r => Math.abs(r.new - r.truth) < Math.abs(r.seoul - r.truth)).length}/${rows.length}`); }
