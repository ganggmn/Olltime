// 과거 공연 저녁을 '그날 실시간으로 돌린 것처럼' 재현: 정답(시간별) → 서울시식 5분 범위(1만 미만 500명, 이상 2,000명 칸, 30분 늦게 들어옴)
// → 지금 사이트 모델(model_main.js)과 새 모델(model_new.js)이 낸 2시간 앞 예상을 정답과 비교.
import fs from 'fs'; import os from 'os';
const H = os.homedir(), SIM = H + '/mnt/(주)한국체육산업개발 공모전/analysis/sim/';
const IN = JSON.parse(fs.readFileSync(H + '/bt/sim_in.json', 'utf8'));
const load = f => { globalThis.OLL = undefined; new Function(fs.readFileSync(SIM + 'gp.js', 'utf8'))(); new Function(fs.readFileSync(SIM + f, 'utf8'))(); return globalThis.OLL; };
const M = { main: load('model_main.js'), new: load('model_new.js') };
const tAt = (tr, t) => { const x = t / 60 - 0.5; if (x <= 0) return tr[0]; if (x >= 23) return tr[23]; const i = Math.floor(x); return tr[i] + (tr[i + 1] - tr[i]) * (x - i); };
const bin = v => { const w = v < 10000 ? 500 : 2000, lo = Math.floor(v / w) * w; return [lo, lo + w]; };
const out = { per: [], charts: {} };
for (const yr of ['2025', '2024']) for (const e of IN[yr]) {
  const list = [];
  for (let m = 0; m < 1440; m += 5) { const v = tAt(e.truth, Math.max(0, m - 30)), [lo, hi] = bin(v); list.push([m, null, lo, hi, '여유', m - 30]); }
  const res = {};
  for (const [nm, O] of Object.entries(M)) { O.EVT[e.d] = [['KSPO DOME', e.st, e.run, e.name]]; res[nm] = O.run(list, { day: e.d, isToday: false }); }
  const score = nm => { let s = 0, a = 0, n = 0, inb = 0; for (const p of res[nm].pPast) { if (p.m < 900 || p.m > 1435) continue; const tv = tAt(e.truth, p.m - 30); s += Math.abs(p.v - tv); a += tv; n++; const [lo, hi] = bin(tv); if (p.v >= lo && p.v <= hi) inb++; } return { mae: s / n, acc: 100 * (1 - s / a), n, inb }; };
  const r = { yr, d: e.d, st: e.st, run: e.run, name: e.name, k: res.new.k, main: score('main'), new: score('new'), exit: e.exit };
  out.per.push(r);
  out.charts[e.d] = { band: list.map(x => [x[0], x[2], x[3]]), truth: list.map(x => [x[0], Math.round(tAt(e.truth, Math.max(0, x[0] - 30)))]),
    main: res.main.pPast.map(p => [p.m, Math.round(p.v)]), new: res.new.pPast.map(p => [p.m, Math.round(p.v)]) };
}
fs.writeFileSync(H + '/bt/sim_out.json', JSON.stringify(out));
for (const yr of ['2025', '2024']) { const P = out.per.filter(p => p.yr === yr); const sm = k => P.reduce((s, p) => s + p[k].mae * p[k].n, 0) / P.reduce((s, p) => s + p[k].n, 0);
  const win = P.filter(p => p.new.mae < p.main.mae).length;
  console.log(yr, '저녁', P.length, '2시간 앞 평균 오차(15~24시) 지금', Math.round(sm('main')), '새', Math.round(sm('new')), '새가 나은 저녁', win + '/' + P.length); }
