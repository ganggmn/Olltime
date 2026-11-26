/* 2시간 앞 사람 수 보정 방식 비교(11/23~26 평일 실시간). 사용: node analysis/ahead_variants.mjs <raw 폴더>
   V0 지금(β 0.94 하나), V1 시간대별 β(2025년 생활인구, 95% 구간이 0을 끼면 0), V2 그 시각의 보통 흔들림(2025년 표준편차×0.84×2)을 넘는 차이는 옮기지 않음,
   V3 앞선 실시간 평일들의 같은 시각 평균 차이로 모양을 고침. 정답은 나중에 나온 올타임 추정값. */
import fs from 'node:fs'; import zlib from 'node:zlib';
await import(new URL('../gp.js', import.meta.url)); await import(new URL('../model.js', import.meta.url)); const OLL=globalThis.OLL;
const dir=(process.argv[2]||'data/citydata').replace(/\/?$/,'/'); // 맥 수집기 원본 raw_YYYYMMDD.jsonl.gz 폴더
const BH={5:0.86,6:1.19,7:1.28,8:1.28,9:1.01,10:0.77,11:0.88,12:1.13,13:1.09,14:0.95,15:0.86,16:0.79,17:0.79,18:0.89,19:0.85,20:0.58,21:0.46};
const SD={5:224,6:327,7:397,8:474,9:705,10:785,11:792,12:697,13:798,14:887,15:935,16:904,17:890,18:870,19:895,20:895,21:796};
const days=['2026-11-23','2026-11-24','2026-11-25','2026-11-26'], D={};
for (const d of days){const txt=zlib.gunzipSync(fs.readFileSync(dir+'raw_'+d.replace(/-/g,'')+'.jsonl.gz')).toString('utf8');const seen=new Map();
  for(const line of txt.split('\n')){if(!line.trim())continue;let p;try{p=JSON.parse(line).response.CITYDATA.LIVE_PPLTN_STTS[0]}catch(e){continue}
    if(!p.PPLTN_TIME.startsWith(d))continue;const m=+p.PPLTN_TIME.slice(11,13)*60+ +p.PPLTN_TIME.slice(14,16);seen.set(m,[m,null,+p.AREA_PPLTN_MIN,+p.AREA_PPLTN_MAX,null]);}
  const list=[...seen.values()].sort((a,b)=>a[0]-b[0]);const r=OLL.run(list,{day:d,isToday:false});const pp=OLL.PP[r.k];
  const cb=m=>r.pn+OLL.hAt(pp.p,m)+(r.k==='wk'?OLL.RIMB*OLL.hAt(pp.rim,m):0);
  D[d]={pe:r.pe,est:new Map(r.pe.map(x=>[x.m,x.v])),cb,btp:r.btp};}
const before=(arr,m)=>{let r=null;for(const c of arr){if(c.m<=m)r=c;else break}return r};
function bias(d,m){ // 앞선 실시간 평일들의 같은 시각(±30분) 평균 차이
  const prev=days.filter(x=>x<d); if(!prev.length)return 0; const v=[];
  for(const x of prev){for(const q of D[x].pe){if(Math.abs(q.m-m)<=30)v.push(q.v-D[x].cb(q.m))}} return v.length?v.reduce((a,b)=>a+b,0)/v.length:0;}
const S=0.84;
function fc(d,m,o){const X=D[d],e0=before(X.pe,m-120);if(!e0)return null;
  const base=mm=>X.cb(mm)+(o.v3?bias(d,mm):0);
  let r=e0.v-base(e0.m); const h=Math.floor(e0.m/60);
  let b=o.v1?(BH[h]??0.94):OLL.bAt(X.btp,120); if(o.cap)b=Math.min(b,1);
  if(o.v2){const lim=2*S*(SD[h]??800); if(Math.abs(r)>lim) r=0;}
  return Math.max(0,base(m)+b*r);}
const V={'V0 지금(0.94 하나)':{}, 'V1 시간대별 β':{v1:1}, 'V1 시간대별 β(1 넘으면 1)':{v1:1,cap:1}, 'V2 범위 벗어난 차이는 안 옮김':{v2:1}, 'V3 최근 실시간 평일로 모양 고침':{v3:1}, 'V1+V2':{v1:1,cap:1,v2:1}, 'V2+V3':{v2:1,v3:1}, 'V1+V2+V3':{v1:1,cap:1,v2:1,v3:1}};
const res={};
for(const [lab,o] of Object.entries(V)){const per=[];let E=0,A=0;
  for(const d of days){let e=0,a=0;for(const q of D[d].pe){if(q.m<420||q.m>1380)continue;const f=fc(d,q.m,o);if(f==null)continue;e+=Math.abs(f-q.v);a+=q.v}
    per.push((100*(1-e/a)).toFixed(1));E+=e;A+=a}
  res[lab]=[(100*(1-E/A)).toFixed(1),per];}
console.log('2시간 앞 정확도(07~23시, 5분마다, 정답 = 나중의 올타임 추정). 합계 | 11/23 11/24 11/25 11/26');
for(const [k,v] of Object.entries(res))console.log(k.padEnd(28),v[0],'|',v[1].join(' '));
// 시간대별 오차(V0 vs V2+V3)
for(const lab of ['V0 지금(0.94 하나)','V2+V3']){const o=V[lab];const bins={};for(const d of days)for(const q of D[d].pe){if(q.m<420||q.m>1380)continue;const f=fc(d,q.m,o);if(f==null)continue;const h=Math.floor(q.m/60);(bins[h]=bins[h]||[]).push(f-q.v)}
  console.log(lab,'시간대별 평균 (예상−실제):',Object.entries(bins).map(([h,v])=>`${h}시 ${Math.round(v.reduce((a,b)=>a+b,0)/v.length)}`).join(' '));}
