import fs from 'fs';
// 공연 중 서울시 값(30분 늦음)을 하나만 쓰지 않고 손에 있는 공연 중 값을 모두 평균해 쓰면 나아지는지(11/27 사후).
// 사용: node analysis/sim/plat_avg_1127.mjs <trend 파일> 2026-11-27 1290 '[1140,1270]' <main의 model.js>
const trendF=process.argv[2], day=process.argv[3]||'2026-11-27', alarm=process.argv[4]?+process.argv[4]:null, mainF=process.argv[6]||'/tmp/model_main.js';
const list=fs.readFileSync(trendF,'utf8').trim().split(';').map(r=>r.split(',').map((v,i)=>i===4?(v||null):(v===''?null:+v)));
const P1='if(pmode){slots.forEach(m=>{if(m<=lastP.m){const e0=before(pe,m-AHEAD)';
const patch=(s,isNew)=>{s=s.replace(P1,'if(pmode){const AH=o.ahead||AHEAD;(o.pslots||slots).forEach(m=>{if(m<=lastP.m){const e0=before(pe,m-AH)');
 if(isNew){s=s.replace('const E=pa?ev[1]+(ev[2]?ev[2]+POST.lag:POST.onset):null;','const E00=pa?ev[1]+(ev[2]?ev[2]+POST.lag:POST.onset):null,Eof=iss=>(pa&&o.alarm!=null&&iss>=o.alarm)?o.alarm-(o.alarmLead==null?20:o.alarmLead):E00;')
  .replace('const fcCell=(m,e0)=>{const f=','const fcCell=(m,e0)=>{const E=Eof(e0.m);'
   // 공연 중 평균: 기준 시각까지 손에 있는 서울시 값 중 측정 시각이 시작+30분~E 사이인 것의 범위 가운데 평균(3개 이상일 때)
   +'const AV=(()=>{if(!o.platAvg)return null;const a=ppl.filter(r=>r[0]<=e0.m&&r[0]-SLAG>=ev[1]+30&&r[0]-SLAG<=E).map(r=>(r[1]+r[2])/2);return a.length>=3?a.reduce((x,y)=>x+y,0)/a.length:null})(),LV=AV!=null?AV:e0.v;const f=')
  .replace('if(m-SLAG<=E){const t0=e0.m-SLAG;return t0>=ev[1]+30&&t0<=E?Math.min(f,e0.v):f}','if(m-SLAG<=E){const t0=e0.m-SLAG;return t0>=ev[1]+30&&t0<=E?(o.platAvg&&AV!=null?AV:Math.min(f,e0.v)):f}')
  .replace('const t0=e0.m-SLAG,inShow=t0>=ev[1]+30&&t0<=E,plat=inShow?e0.v:','const t0=e0.m-SLAG,inShow=t0>=ev[1]+30&&t0<=E,plat=inShow?LV:(o.platAvg&&AV!=null&&t0>E&&t0<=E+10?AV:0)||');}
 return s};
const load=(src,isNew)=>{globalThis.OLL=undefined;new Function(fs.readFileSync(new URL('../../gp.js',import.meta.url),'utf8'))();const s=patch(fs.readFileSync(src,'utf8'),isNew);if(isNew&&!s.includes('platAvg'))throw 'patch';new Function(s)();return globalThis.OLL};
const MAIN=load(mainF,false),NEW=load(new URL('../../model.js',import.meta.url),true);
const ps=[];for(let m=0;m<1440;m+=5)ps.push(m);
const V={'지금 사이트':[MAIN,{}],'새':[NEW,{}],'새+공연중 평균':[NEW,{platAvg:1}]};
if(alarm!=null){V['새+알림L20']=[NEW,{alarm,alarmLead:20}];V['새+알림L20+평균']=[NEW,{alarm,alarmLead:20,platAvg:1}];V['새+알림L5']=[NEW,{alarm,alarmLead:5}];V['새+알림L5+평균']=[NEW,{alarm,alarmLead:5,platAvg:1}]}
const ev=JSON.parse(process.argv[5]||'null');
const st=ev?ev[0]:1140, en=ev?ev[1]:1140+130;
const W={'공연 중':[st+60,en+30],'끝난 뒤':[en+30,1435],'시작~24시':[st,1435]};
for(const ah of [120,60,30]){console.log('---',ah+'분 앞');for(const [nm,[O,opt]] of Object.entries(V)){const R=O.run(list,{day,isToday:false,ahead:ah,pslots:ps,...opt});
 const est=new Map(R.pe.map(p=>[p.m,p.v])),rg=new Map(R.ppl.map(r=>[r[0],r])),f=new Map(R.pPast.map(p=>[p.m,p.v]));
 console.log(nm.padEnd(14),Object.entries(W).map(([w,[a,b]])=>{let e=0,t=0,n=0,ib=0;for(const [m,v] of est){if(m<a||m>b||!f.has(m))continue;e+=Math.abs(f.get(m)-v);t+=v;n++;const r=rg.get(m);if(r&&f.get(m)>=r[1]-1&&f.get(m)<=r[2]+1)ib++}return `${w} ${(100*(1-e/t)).toFixed(1)}%(범위안 ${Math.round(100*ib/n)}%)`}).join(' | '))}}
