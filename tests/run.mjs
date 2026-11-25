/* 올타임 자동 점검. 설치할 것 없이 `npm test`로 돌려요(Node 20 이상).
   화면 코드가 깨지지 않았는지, 화면끼리 숫자가 어긋나지 않는지, 경로 계산과 서버 함수가 기대대로 도는지 봐요. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const rd = f => fs.readFileSync(path.join(ROOT, f), 'utf8');
let pass = 0; const fails = [];
const test = async (name, fn) => { try { await fn(); pass++; console.log('  통과  ' + name); } catch (e) { fails.push(name); console.log('  실패  ' + name + '\n        ' + String(e.message).split('\n')[0]); } };
const ok = (c, m) => { if (!c) throw new Error(m || '조건이 거짓'); };
const near = (a, b, tol, m) => ok(Math.abs(a - b) <= tol, `${m || ''} ${a} ≠ ${b} (허용 ${tol})`);
const scripts = html => [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const constOf = (src, name) => { const m = src.match(new RegExp('const ' + name + '=([\\s\\S]*?);\\n')); ok(m, name + ' 없음'); return new Function('return ' + m[1])(); };

const PAGES = ['index.html', 'trend.html', 'ops.html', 'sections.html', 'verify.html', 'privacy.html', 'terms.html'];
console.log('1. 화면 코드');
for (const f of PAGES) await test(`${f}: 스크립트 문법`, () => { for (const s of scripts(rd(f))) new Function('return (async()=>{' + s.replace(/^\s*\(async\(\)=>\{/, '').replace(/\}\)\(\);?\s*$/, '') + '\n})'); });
await test('미완성 표시가 남아 있지 않음', () => { for (const f of PAGES) { const h = rd(f); for (const w of ['[운영자 이름]', '[연락 이메일]', '반영 중', 'TODO']) ok(!h.includes(w), `${f}에 "${w}"`); } ok(!/<h1>[^<]*시안/.test(rd('sections.html')), 'sections 제목에 시안'); });
await test('index.html이 src와 같은 내용으로 만들어져 있음', () => { const idx = rd('index.html'), app = rd('src/app.js'); for (const probe of ['const NLV=', "['지난주 실측',", 'id="tnow"']) ok(idx.includes(probe) === (app + rd('src/body.html')).includes(probe), probe + ' 불일치: src/assemble.py를 다시 돌리세요'); });

console.log('2. 화면끼리 숫자');
const app = rd('src/app.js'), body = rd('src/body.html'), verify = rd('verify.html'), ops = rd('ops.html'), sec = rd('sections.html'), trend = rd('trend.html');
await test('정확도 표: 첫 화면과 검증 기록이 같음', () => { const lad = [...app.matchAll(/\['[^']+',(\d+\.\d),'/g)].map(m => m[1]); ok(lad.length === 6, '단계 수 ' + lad.length); for (const v of lad) ok(verify.includes(`<td>${v}%</td>`), `검증 기록에 ${v}% 없음`); ok(body.includes(`${lad[4]}% → ${lad[5]}%`), '첫 화면 큰 숫자가 표와 다름'); });
await test('검증 기록 목차 수 = 본문 항목 수', () => { const toc = (verify.match(/<li><a href="#v\d+">/g) || []).length, secs = (verify.match(/<section id="v\d+">/g) || []).length; ok(toc === secs, `목차 ${toc} 본문 ${secs}`); ok(body.includes(`검증 기록 ${secs}건`), '첫 화면의 건수'); });
await test('주차 새벽 바닥 보정값: 추이와 운영판이 같음', () => { const a = +trend.match(/const FLOOR=(\d+)/)[1], b = +ops.match(/FLOOR=(\d+)/)[1]; ok(a === b, `${a} ≠ ${b}`); });
await test('차이가 남는 비율 표: 추이와 운영판이 같음', () => { const g = s => s.match(/const BETA=(\{[^;]+\})[,;]/)[1].replace(/\s/g, ''); ok(g(trend) === g(ops), '표가 다름'); });
const KER = constOf(ops, 'KER'), GOUT = constOf(ops, 'GOUT'), GIN = constOf(ops, 'GIN'), TOT = +ops.match(/const TOT=(\d+)/)[1], LAG = +ops.match(/LAG=(\d+)/)[1];
const F = new Function('return ' + sec.match(/const F=(\{[^;]+\});/)[1])();
await test('10분 곡선의 몫을 모두 더하면 100%', () => near(KER.reduce((a, b) => a + b, 0), 100, 1.5));
await test('구간 혼잡도의 역 방향 사람 수 = 승차 증가 합 × 10분 곡선', () => { const h1 = KER.slice(3, 9).reduce((a, b) => a + b, 0) / 100 * TOT, h2 = KER.slice(9, 15).reduce((a, b) => a + b, 0) / 100 * TOT; near(F.e[4], h1, h1 * .02, '끝난 뒤 1시간'); near(F.e[5], h2, 30, '그다음 1시간'); });
await test('구간 혼잡도의 북2문 사람 수 = 10분 출차 합 × 2명', () => { near(F.n[4], 2 * GOUT.n.slice(3, 9).reduce((a, b) => a + b, 0), 20); near(F.n[5], 2 * GOUT.n.slice(9, 15).reduce((a, b) => a + b, 0), 20); });
await test('곡선 길이: 시작 전 21칸, 끝난 뒤 15칸', () => { ok(KER.length === 15); for (const k of ['n', 'd', 's']) { ok(GOUT[k].length === 15, 'GOUT.' + k); ok(GIN[k].length === 21, 'GIN.' + k); } });

console.log('3. 운영판 계산');
const opsJs = scripts(ops).pop();
const calcSrc = opsJs.slice(opsJs.indexOf('const $='), opsJs.indexOf('function render()'));
const calcEnv = new Function('document', 'matchMedia', calcSrc + '\nreturn {calc,mk,runs,TOT,LAG,AUD0,W_HOT,C_WARN};');
const O = calcEnv({ querySelector: () => ({}) }, () => ({ matches: false }));
await test('관객이 기준(13,452명)이면 역 방향 합이 승차 증가 합과 같음', () => { const o = O.calc([{ v: 'KSPO DOME', s: 1020, e: 1170, a: O.AUD0 }]); near([...o.we].reduce((a, b) => a + b, 0), O.TOT, O.TOT * .02); });
await test('관객 수에 비례함', () => { const a = O.calc([{ s: 1020, e: 1170, a: 13452 }]).pk, b = O.calc([{ s: 1020, e: 1170, a: 6726 }]).pk; near(b, a / 2, 1); });
await test('가장 붐비는 10분은 끝 시각 + 25분 + 10~20분', () => { const o = O.calc([{ s: 1020, e: 1170, a: 13452 }]); near(o.pt, 1170 + O.LAG + 10, 10); });
await test('공연 두 개는 하나씩 계산한 값의 합', () => { const A = { s: 1020, e: 1170, a: 13000 }, B = { s: 1080, e: 1230, a: 3000 }; const s = O.calc([A, B]).we, a = O.calc([A]).we, b = O.calc([B]).we; for (let i = 0; i < s.length; i++) near(s[i], a[i] + b[i], 1e-6); });
await test('끝나는 시각을 30분 늦추면 최고 시각도 30분 늦어짐', () => near(O.calc([{ s: 1020, e: 1200, a: 13000 }]).pt - O.calc([{ s: 1020, e: 1170, a: 13000 }]).pt, 30, 0));

console.log('4. 공연 일정');
const data = rd('src/data/data.js'), travel = rd('src/data/travel.js');
const { TR, ROUTE, SHOWS } = new Function(data + '\n' + travel + '\nreturn {TR,ROUTE,SHOWS};')();
await test('공연 목록: 날짜순, 시각 형식, 아는 공연장', () => { const V = new Set(['KSPO DOME', '올림픽홀', '핸드볼경기장', '티켓링크 라이브 아레나', '우리금융아트홀', '88잔디마당', 'K-아트홀', '뮤즈라이브', '수변무대', 'SK핸드볼경기장']); let prev = ''; for (const s of SHOWS) { ok(/^\d{4}-\d{2}-\d{2}$/.test(s.d) && /^\d{2}:\d{2}$/.test(s.t), JSON.stringify(s).slice(0, 60)); ok(s.d >= prev, '날짜 순서 ' + s.d); prev = s.d; ok(V.has(s.venue), '모르는 공연장 ' + s.venue); } });
await test('운영판의 공연이 공연 목록과 같음(공연장, 시작 시각)', () => { const EVT = constOf(ops, 'EVT'); for (const [d, list] of Object.entries(EVT)) { const real = SHOWS.filter(s => s.d === d && ['KSPO DOME', '올림픽홀', '핸드볼경기장'].includes(s.venue)); if (!real.length) continue; ok(real.length === list.length, `${d}: 목록 ${real.length}개, 운영판 ${list.length}개`); for (const s of real) { const m = +s.t.slice(0, 2) * 60 + +s.t.slice(3); ok(list.some(e => e[0] === s.venue && e[1] === m && (!s.run || e[2] === s.run)), `${d} ${s.venue} ${s.t}`); } } });
await test('추이의 공연 표시가 공연 목록의 KSPO DOME 시작 시각과 같음', () => { const EVT = constOf(trend, 'EVT'); for (const [d, list] of Object.entries(EVT)) { const s = SHOWS.find(x => x.d === d && x.venue === 'KSPO DOME'); if (!s) continue; ok(list[0][0] === +s.t.slice(0, 2) * 60 + +s.t.slice(3), d); } });

console.log('5. 지하철 경로');
const ST = ROUTE.st.map(x => x[0]), L9 = ROUTE.ln.indexOf('9호선');
const exp9 = new Set(ROUTE.e.filter(e => e[2] === L9 && e[3]).flatMap(e => [ST[e[0]], ST[e[1]]]));
await test('9호선 급행 정차역: 올림픽공원·석촌·종합운동장·봉은사는 서고 한성백제는 안 섬', () => { for (const n of ['올림픽공원', '석촌', '종합운동장', '봉은사', '김포공항', '여의도']) ok(exp9.has(n), n + ' 없음'); for (const n of ['한성백제', '송파나루', '둔촌오륜', '삼전']) ok(!exp9.has(n), n + '가 급행 정차역으로 들어 있음'); });
const dest = TR.find('올림픽공원')[0], legs = n => TR.transit(TR.find(n)[0], dest).legs;
await test('김포공항 → 올림픽공원: 9호선 급행 한 번', () => { const l = legs('김포공항'); ok(l.length === 1 && l[0].line === '9호선' && l[0].exp, JSON.stringify(l)); });
await test('급행 구간과 일반 구간이 한 줄로 합쳐지지 않음', () => { for (const n of ['강남', '잠실', '노원', '인천', '수원', '삼성중앙']) { const h = TR.find(n); if (!h.length) continue; for (const l of TR.transit(h[0], dest).legs) if (l.line === '9호선' && l.exp) ok(exp9.has(l.from) && exp9.has(l.to), `${n}: 급행이 ${l.from}→${l.to}`); } });
await test('없는 역은 찾지 못함', () => ok(TR.find('부산역').length === 0));

console.log('6. 서버 함수');
const mkRes = () => { const r = { code: 0, body: null, h: {}, setHeader(k, v) { r.h[k] = v; }, status(c) { r.code = c; return r; }, json(b) { r.body = b; return r; } }; return r; };
const trendFn = (await import(path.join(ROOT, 'api/trend.js'))).default;
await test('추이: 저장소 키가 없으면 ok:false', async () => { delete process.env.SUPABASE_URL; delete process.env.SUPABASE_SERVICE_KEY; const r = mkRes(); await trendFn({ query: {} }, r); ok(r.code === 200 && r.body.ok === false); });
await test('추이: 기록을 [분, 주차, 아래, 위, 단계]로 바꿔 돌려줌', async () => { process.env.SUPABASE_URL = 'https://example.invalid'; process.env.SUPABASE_SERVICE_KEY = 'test-key'; const real = globalThis.fetch; let url = ''; globalThis.fetch = async u => { url = String(u); return { ok: true, json: async () => [{ ts: '2026-11-22T08:10:00Z', parking: 2000, ppl_lo: 9000, ppl_hi: 9500, lvl: '보통' }] }; }; const r = mkRes(); await trendFn({ query: { day: '2026-11-22' } }, r); globalThis.fetch = real; ok(r.body.ok && r.body.n === 1, JSON.stringify(r.body)); ok(r.body.list[0].join() === '1030,2000,9000,9500,보통', r.body.list[0].join()); ok(url.includes('samples') && url.includes('2026-11-21T15%3A00'), '하루 범위가 한국 시간 0시부터가 아님'); ok(!JSON.stringify(r.body).includes('test-key'), '응답에 키가 들어 있음'); });
await test('추이: 날짜 형식이 틀리면 오늘로', async () => { const real = globalThis.fetch; globalThis.fetch = async () => ({ ok: true, json: async () => [] }); const r = mkRes(); await trendFn({ query: { day: "2026-11-22';drop" } }, r); globalThis.fetch = real; ok(/^\d{4}-\d{2}-\d{2}$/.test(r.body.day)); });
await test('추이: 저장소가 실패하면 502', async () => { const real = globalThis.fetch; globalThis.fetch = async () => ({ ok: false, status: 500 }); const r = mkRes(); await trendFn({ query: {} }, r); globalThis.fetch = real; ok(r.code === 502 && r.body.ok === false); });
await test('저장소 코드에 키 값이 적혀 있지 않음', () => { for (const f of fs.readdirSync(path.join(ROOT, 'api'))) { const s = rd('api/' + f); ok(!/eyJ[A-Za-z0-9_-]{20,}/.test(s) && !/sb_secret_/.test(s), f + '에 키처럼 보이는 문자열'); } });

console.log(`\n${pass}개 통과, ${fails.length}개 실패`);
if (fails.length) { console.log('실패: ' + fails.join(' / ')); process.exit(1); }
