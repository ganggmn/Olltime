/* 올타임 계산 한곳 모음: 추이 화면, 운영판, 서버의 자동 채점, 자동 점검이 모두 이 파일의 같은 함수를 써요.
   브라우저에서는 <script src="/model.js">, 서버와 점검에서는 import '../model.js' 로 불러요. gp.js(2025년 문별 주차 대수)가 먼저 있어야 해요. */
(function(){
/* 예상과 실제의 차이가 시간이 지나며 얼마나 남는지: 2025년 215일 입출차 기록(20분 간격, 8시간까지). analysis/beta.py */
const BETA={show:[0.98,0.95,0.92,0.89,0.87,0.85,0.84,0.83,0.81,0.78,0.75,0.72,0.68,0.65,0.62,0.59,0.56,0.54,0.52,0.5,0.49,0.48,0.47,0.46],noshow:[0.99,0.97,0.95,0.92,0.9,0.88,0.86,0.84,0.82,0.8,0.77,0.75,0.73,0.71,0.69,0.67,0.66,0.65,0.64,0.63,0.63,0.63,0.63,0.63]};
/* 실시간 값의 새벽 바닥(1,032대)에서 2025년 입출차 기록의 새벽 값(127대)을 뺀 차이. analysis/crosscheck.py */
const FLOOR=905;
/* 차 한 대당 방문객 수(2025년 입출차 기록과 생활인구, 동2·남2·북2문 기준). analysis/coef.py */
const KC={wk:[[9,3.3],[11,3.7],[13,4.1],[15,4.3],[17,4.4],[19,3.6],[21,3.6]],show:[[9,3.2],[11,4.1],[13,4.8],[15,5.6],[17,7.9],[19,9.5],[21,12.1]]};
const AHEAD=120;
/* 큰 공연 일정: [공연장, 시작(0시부터 몇 분), 공연 길이(분, 공연 안내에 있을 때만), 이름]. 첫 화면의 공연 목록과 같아야 해요(자동 점검이 확인). */
const EVT={'2026-11-22':[['KSPO DOME',1020,0,'로이킴']],'2026-11-27':[['KSPO DOME',1140,130,'조용필'],['올림픽홀',1200,0,'다이나믹 듀오']],'2026-11-28':[['KSPO DOME',1080,130,'조용필'],['올림픽홀',1080,0,'다이나믹 듀오']],'2026-11-29':[['KSPO DOME',1020,130,'조용필'],['올림픽홀',1020,0,'다이나믹 듀오']],'2026-12-04':[['KSPO DOME',1140,120,'이승철']],'2026-12-05':[['KSPO DOME',960,120,'이승철'],['올림픽홀',1080,120,'비']],'2026-12-06':[['KSPO DOME',960,120,'이승철'],['올림픽홀',1020,120,'비']]};
const bAt=(t,h)=>{if(h<=0)return 1;const x=h/20;if(x<=1)return 1+(t[0]-1)*x;const i=Math.min(t.length-1,Math.floor(x)-1),j=Math.min(t.length-1,i+1);return t[i]+(t[j]-t[i])*(x-i-1)};
const kAt=(t,m)=>{const h=m/60;if(h<=t[0][0])return t[0][1];for(let i=1;i<t.length;i++)if(h<=t[i][0])return t[i-1][1]+(t[i][1]-t[i-1][1])*(h-t[i-1][0])/(t[i][0]-t[i-1][0]);return t[t.length-1][1]};
const hm=m=>{m=((Math.round(m)%1440)+1440)%1440;return String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0')};
const num=n=>Math.round(n).toLocaleString('ko-KR');
const med=a=>{const b=a.slice().sort((x,y)=>x-y);return b.length?b[Math.floor(b.length/2)]:null};
/* 큰 공연(KSPO DOME)이 있는 날인지, 날의 종류(평일·금·토·일, 공연 유무) */
const bigShow=d=>!!(EVT[d]&&EVT[d].some(e=>e[0]==='KSPO DOME'));
const clsOf=d=>{const wd=new Date(d+'T12:00:00+09:00').getUTCDay(),base=wd===0?'hol':wd===6?'sat':wd===5?'fri':'wk';return bigShow(d)&&base!=='wk'?base+'_show':base};
/* 서울시 범위만 있을 때: 범위가 바뀌는 순간들을 이어서 한 숫자로 */
function estimate(rows){const mid=rows.map(r=>(r[1]+r[2])/2),kt=[],kv=[];
  for(let i=1;i<rows.length;i++){const a=rows[i-1],b=rows[i];if(a[1]!==b[1]){const w=a[2]-a[1];if(Math.abs(b[1]-a[1])<=w*1.5||Math.abs(b[2]-a[2])<=w*1.5){kt.push((a[0]+b[0])/2);kv.push(b[1]>a[1]?b[1]:b[2])}else{kt.push(b[0]);kv.push(mid[i])}}}
  return rows.map((r,i)=>{if(kt.length<2||r[0]<kt[0]||r[0]>kt[kt.length-1])return mid[i];let j=1;while(kt[j]<r[0])j++;const v=kv[j-1]+(kv[j]-kv[j-1])*(r[0]-kt[j-1])/(kt[j]-kt[j-1]);return Math.min(r[2],Math.max(r[1],v))})}
/* 새벽(02:00~04:30)의 주차 대수와 사람 수: 그날의 바닥 */
function carCtx(rows,car){const pick=(lo,hi)=>[...car].filter(([m])=>m>=lo&&m<=hi).map(x=>x[1]);
  if(car.size<6||!rows.length)return null;let night=pick(120,270);if(!night.length)night=pick(0,270);if(!night.length)return null;
  let pn=rows.filter(r=>r[0]>=120&&r[0]<=270).map(r=>(r[1]+r[2])/2);if(!pn.length)pn=rows.filter(r=>r[0]<=270).map(r=>(r[1]+r[2])/2);
  return{cf:med(night),pf:pn.length?med(pn):rows[0][1]}}
/* 주차 대수가 있을 때: 주차 대수로 사람 수의 모양을 만들고, 서울시 범위가 한 칸 바뀌는 순간마다 높이를 다시 맞춤 */
function estimate2(rows,car,tab,ctx){const cf=ctx.cf,pf=ctx.pf;let off=null,lastCar=null;
  return rows.map((r,i)=>{const c=car.has(r[0])?car.get(r[0]):lastCar;if(c==null)return (r[1]+r[2])/2;lastCar=c;const model=pf+kAt(tab,r[0])*Math.max(0,c-cf);
    if(off===null)off=(r[1]+r[2])/2-model;
    if(i>0){const a=rows[i-1];if(a[1]!==r[1]){const w=a[2]-a[1];off=(Math.abs(r[1]-a[1])<=w*1.5||Math.abs(r[2]-a[2])<=w*1.5)?(r[1]>a[1]?r[1]:r[2])-model:(r[1]+r[2])/2-model}}
    return Math.min(r[2],Math.max(r[1],model+off))})}
/* 하루 기록 [[분, 주차, 인원 아래, 인원 위, 단계], ...]에서 추정과 예상을 모두 계산.
   단계: ①기록 정리 → ②사람 수 추정 → ③주차 예상 → ④사람 수 예상 */
function run(list,o){const day=o.day,isToday=!!o.isToday,isShow=bigShow(day),k=clsOf(day),bt=BETA[isShow?'show':'noshow'],tab=KC[isShow?'show':'wk'];
  /* ① 기록 정리: 값이 없는 줄을 빼고, 앞뒤보다 1.6배 넘게 혼자 튄 인원 값 하나는 뺌 */
  let ppl=list.filter(r=>r[2]!=null&&r[3]!=null).map(r=>[r[0],r[2],r[3]]);
  const odd=ppl.filter((r,i)=>i>0&&i<ppl.length-1&&r[2]>1.6*ppl[i-1][2]&&r[2]>1.6*ppl[i+1][2]);ppl=ppl.filter(r=>!odd.includes(r));
  const car=list.filter(r=>r[1]!=null).map(r=>({m:r[0],v:r[1]})),carMap=new Map(car.map(c=>[c.m,c.v]));
  /* ② 사람 수 추정 */
  const ctx=carCtx(ppl,carMap),est2=ctx?estimate2(ppl,carMap,tab,ctx):null,est=est2||estimate(ppl);
  /* ③ 주차 예상: 2025년 같은 종류 날의 가운데값 + (기준 시각의 실제 값과 예상의 차이 × 그 차이가 남는 비율) */
  const profAll=GP.slots_min.map((m,i)=>({m,v:['북2문','동2문','남2문'].reduce((a,g)=>a+GP.gates[g][k][i],0)+FLOOR}));
  const pAt=m=>{const i=Math.max(0,Math.min(71,Math.floor(m/20))),a=profAll[i],b=profAll[Math.min(71,i+1)];return a.v+(b.v-a.v)*(m-a.m)/20};
  const before=(arr,m)=>{let r=null;for(const c of arr){if(c.m<=m)r=c;else break}return r};
  const fcCar=(m,c0)=>Math.max(0,pAt(m)+bAt(bt,m-c0.m)*(c0.v-pAt(c0.m)));
  const lastCar=car[car.length-1],slots=GP.slots_min.concat([1440]),carPast=[],carFut=[];
  if(car.length>=6){slots.forEach(m=>{if(m<=lastCar.m){const c0=before(car,m-AHEAD);if(c0)carPast.push({m,v:fcCar(m,c0)})}else if(isToday&&lastCar.m<1400)carFut.push({m,v:fcCar(m,lastCar)})});if(carFut.length)carFut.unshift({m:lastCar.m,v:lastCar.v})}
  /* ④ 사람 수 예상: 주차 예상에 '차 한 대당 방문객 수'를 곱하고, 기준 시각의 추정값과의 차이를 같은 비율로 더함 */
  const pe=ppl.map((r,i)=>({m:r[0],v:est[i]})),lastP=pe[pe.length-1],shape=ctx?(m,c)=>ctx.pf+kAt(tab,m)*Math.max(0,c-ctx.cf):null;
  const fcPpl=(m,c0,e0)=>Math.max(0,shape(m,fcCar(m,c0))+bAt(bt,m-c0.m)*(e0.v-shape(c0.m,c0.v)));
  const pPast=[],pFut=[];
  if(shape&&est2&&car.length>=6&&lastP){slots.forEach(m=>{if(m<=lastP.m){const c0=before(car,m-AHEAD),e0=before(pe,m-AHEAD);if(c0&&e0)pPast.push({m,v:fcPpl(m,c0,e0)})}else if(isToday&&lastP.m<1400)pFut.push({m,v:fcPpl(m,lastCar,lastP)})});if(pFut.length)pFut.unshift({m:lastP.m,v:lastP.v})}
  return{day,k,isShow,nd:GP.n[k]||0,bt,ppl,odd,car,carMap,ctx,est,hasEst2:!!est2,pe,profAll,pAt,fcCar,carPast,carFut,pPast,pFut}}
/* ⑤ 채점용 오차 목록: 2시간 앞서 낸 예상과 실제(주차) 또는 추정(사람 수)의 차이 */
function errors(R){const rowAt=new Map(R.ppl.map(r=>[r[0],r])),em=new Map(R.pe.map(p=>[p.m,p.v]));
  return{car:R.carPast.filter(p=>R.carMap.has(p.m)).map(p=>({m:p.m,f:p.v,a:R.carMap.get(p.m),e:Math.abs(p.v-R.carMap.get(p.m))})),
    ppl:R.pPast.filter(p=>em.has(p.m)).map(p=>{const r=rowAt.get(p.m),a=em.get(p.m);return{m:p.m,f:p.v,a,e:Math.abs(p.v-a),inb:p.v>=r[1]&&p.v<=r[2]}})}}
/* ⑥ 이상 징후: 기준은 운영자가 정해요. 비어 있는 기준은 쓰지 않아요.
   rules={win:몇 분 사이, dn:사람 수가 몇 명 넘게 변함, dp:몇 % 넘게 변함, k:평소 오차의 몇 배 넘게 빗나감(소수 한 자리)}, usual={car,ppl}: 평소 오차 */
function anomalies(R,E,rules,usual){const ev=[],r=rules||{},win=+r.win>0?+r.win:null;
  if(win&&(+r.dn>0||+r.dp>0)){const pe=R.pe;let j=0;for(let i=0;i<pe.length;i++){while(j<i&&pe[j+1].m<=pe[i].m-win)j++;const a=pe[j],b=pe[i];if(b.m-a.m<win||b.m-a.m>win+10)continue;const d=b.v-a.v,pct=a.v>0?Math.abs(d)/a.v*100:0,byN=+r.dn>0&&Math.abs(d)>=+r.dn,byP=+r.dp>0&&pct>=+r.dp;
    if(byN||byP)ev.push({m:b.m,from:a.m,kind:'jump',text:`${hm(a.m)}부터 ${win}분 사이 공원 안 사람이 약 ${num(Math.abs(d)/100)*100<100?num(Math.abs(d)):num(Math.round(Math.abs(d)/100)*100)}명(${pct.toFixed(1)}%) ${d<0?'줄었어요':'늘었어요'}`})}}
  if(+r.k>0&&usual){for(const [key,unit,name] of [['car','대','주차 예상'],['ppl','명','사람 수 예상']]){const u=usual[key];if(!(u>0))continue;for(const x of E[key])if(x.e>=+r.k*u)ev.push({m:x.m,from:x.m-AHEAD,kind:'err',text:`${hm(x.m)}의 ${name}이 ${num(x.e)}${unit} 빗나갔어요(평소 ${num(u)}${unit}의 ${(x.e/u).toFixed(1)}배)`})}}
  ev.sort((a,b)=>a.m-b.m);
  /* 같은 일로 이어지는 알림은 하나로: 30분 안에 이어지면 처음 것만 남기고 끝 시각을 늘림 */
  const out=[];for(const e of ev){const l=out[out.length-1];if(l&&l.kind===e.kind&&e.m-l.to<=30){l.to=e.m;l.n++}else out.push({...e,to:e.m,n:1})}
  return out}
const stat=(xs)=>{if(!xs.length)return{n:0,mae:null,pct:null};const mae=xs.reduce((s,x)=>s+x.e,0)/xs.length,pct=xs.reduce((s,x)=>s+(x.a>0?x.e/x.a:0),0)/xs.length*100;return{n:xs.length,mae:Math.round(mae*10)/10,pct:Math.round(pct*10)/10}};
/* ⑦ 하루 채점: 전체와, 이상 징후로 표시된 시간(시작부터 끝 뒤 2시간까지)을 뺀 것 두 가지 */
function score(list,o){const R=run(list,{day:o.day,isToday:false}),E=errors(R),ev=anomalies(R,E,o.rules,o.usual);
  const inEv=m=>ev.some(e=>m>=e.from&&m<=e.to+AHEAD),carX=E.car.filter(x=>!inEv(x.m)),pplX=E.ppl.filter(x=>!inEv(x.m));
  const P=stat(E.ppl),PX=stat(pplX);P.inband=E.ppl.length?Math.round(E.ppl.filter(x=>x.inb).length/E.ppl.length*100):null;PX.inband=pplX.length?Math.round(pplX.filter(x=>x.inb).length/pplX.length*100):null;
  return{day:o.day,kind:R.k,records:list.length,car:stat(E.car),carEx:stat(carX),ppl:P,pplEx:PX,events:ev.map(e=>({from:hm(e.from),at:hm(e.m),to:hm(e.to),kind:e.kind,text:e.text})),errs:{car:E.car.map(x=>x.e),ppl:E.ppl.map(x=>x.e)}}}
/* 여러 날을 한 번에: 평소 오차(모든 날 오차의 가운데값)를 먼저 구하고 그걸로 이상 징후를 판정 */
function scoreDays(byDay,rules){const days=Object.keys(byDay).sort(),first=days.map(d=>score(byDay[d],{day:d}));
  const usual={car:med(first.flatMap(s=>s.errs.car)),ppl:med(first.flatMap(s=>s.errs.ppl))};
  const out=days.map(d=>{const s=score(byDay[d],{day:d,rules,usual});delete s.errs;return s});
  const tot=k=>{const xs=out.filter(s=>s[k].n);const n=xs.reduce((a,s)=>a+s[k].n,0);return n?{n,mae:Math.round(xs.reduce((a,s)=>a+s[k].mae*s[k].n,0)/n*10)/10,pct:Math.round(xs.reduce((a,s)=>a+s[k].pct*s[k].n,0)/n*10)/10}:{n:0,mae:null,pct:null}};
  return{rules:rules||{},usual:{car:usual.car==null?null:Math.round(usual.car),ppl:usual.ppl==null?null:Math.round(usual.ppl)},days:out,total:{car:tot('car'),carEx:tot('carEx'),ppl:tot('ppl'),pplEx:tot('pplEx')}}}
/* 운영자가 넣은 기준을 숫자로: 분·명은 정수, %와 배수는 소수 한 자리 */
function cleanRules(q){const f=(v,dec,lo,hi)=>{const n=Number(v);if(!isFinite(n)||n<=0)return null;const r=dec?Math.round(n*10)/10:Math.round(n);return Math.min(hi,Math.max(lo,r))};
  return{win:f(q.win,0,5,180),dn:f(q.dn,0,1,100000),dp:f(q.dp,1,0.1,1000),k:f(q.k,1,0.1,100)}}
globalThis.OLL={BETA,FLOOR,KC,AHEAD,EVT,bAt,kAt,hm,num,med,bigShow,clsOf,estimate,carCtx,estimate2,run,errors,anomalies,score,scoreDays,cleanRules};
})();
