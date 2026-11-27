/* 서울시 범위 안에 들었나(2026-11-27): 실시간 평일 11/23~26, 07~23시 5분마다, 사이트의 새벽 예상과 2시간 앞 예상이 서울시가 낸 인구 범위(최소~최대) 안에 든 비율.
   사용: node analysis/live_range_hit.mjs <raw 폴더>
   (원래 설명) 지금 기준 재검증(2026-11-27): 실시간 평일 11/23~26에서 사이트 방식의 '새벽 예상'(그날 새벽 수준 + 평일 모양)과 '2시간 앞'(V0, β 0.94) 정확도를 날마다 내요.
   사용: node analysis/live_recheck_pop.mjs <raw 폴더> > analysis/live_recheck_pop_20261123_26.json
   (아래는 ahead_variants.mjs와 같은 읽기 부분)
   V0 지금(β 0.94 하나), V1 시간대별 β(2025년 생활인구, 95% 구간이 0을 끼면 0), V2 그 시각의 보통 흔들림(2025년 표준편차×0.84×2)을 넘는 차이는 옮기지 않음,
   V3 앞선 실시간 평일들의 같은 시각 평균 차이로 모양을 고침. 정답은 나중에 나온 올타임 추정값. */
import fs from 'node:fs'; import zlib from 'node:zlib';
await import(new URL('../gp.js', import.meta.url)); await import(new URL('../model.js', import.meta.url)); const OLL=globalThis.OLL;
const dir=(process.argv[2]||'data/citydata').replace(/\/?$/,'/'); // 맥 수집기 원본 raw_YYYYMMDD.jsonl.gz 폴더
const BH={5:0.86,6:1.19,7:1.28,8:1.28,9:1.01,10:0.77,11:0.88,12:1.13,13:1.09,14:0.95,15:0.86,16:0.79,17:0.79,18:0.89,19:0.85,20:0.58,21:0.46};
const SD={5:224,6:327,7:397,8:474,9:705,10:785,11:792,12:697,13:798,14:887,15:935,16:904,17:890,18:870,19:895,20:895,21:796};
const days=['2026-11-23','2026-11-24','2026-11-25','2026-11-26'], D={}, RG=new Map();
for (const d of days){const txt=zlib.gunzipSync(fs.readFileSync(dir+'raw_'+d.replace(/-/g,'')+'.jsonl.gz')).toString('utf8');const seen=new Map();
  for(const line of txt.split('\n')){if(!line.trim())continue;let p;try{p=JSON.parse(line).response.CITYDATA.LIVE_PPLTN_STTS[0]}catch(e){continue}
    if(!p.PPLTN_TIME.startsWith(d))continue;const m=+p.PPLTN_TIME.slice(11,13)*60+ +p.PPLTN_TIME.slice(14,16);seen.set(m,[m,null,+p.AREA_PPLTN_MIN,+p.AREA_PPLTN_MAX,null]);RG.set(d+' '+m,[+p.AREA_PPLTN_MIN,+p.AREA_PPLTN_MAX,p.AREA_CONGEST_LVL]);}
  const list=[...seen.values()].sort((a,b)=>a[0]-b[0]);const r=OLL.run(list,{day:d,isToday:false});const pp=OLL.PP[r.k];
  const cb=m=>r.pn+OLL.hAt(pp.p,m)+(r.k==='wk'?OLL.RIMB*OLL.hAt(pp.rim,m):0);
  D[d]={pe:r.pe,est:new Map(r.pe.map(x=>[x.m,x.v])),cb,btp:r.btp};}
const before=(arr,m)=>{let r=null;for(const c of arr){if(c.m<=m)r=c;else break}return r};
function bias(d,m){ // 앞선 실시간 평일들의 같은 시각(±30분) 평균 차이
  const prev=days.filter(x=>x<d); if(!prev.length)return 0; const v=[];
  for(const x of prev){for(const q of D[x].pe){if(Math.abs(q.m-m)<=30)v.push(q.v-D[x].cb(q.m))}} return v.length?v.reduce((a,b)=>a+b,0)/v.length:0;}


function fc(d,m){const X=D[d],e0=before(X.pe,m-120);if(!e0)return null;const r=e0.v-X.cb(e0.m);return Math.max(0,X.cb(m)+OLL.bAt(X.btp,120)*r);}
const res={dawn:[0,0,0,0],h2:[0,0,0,0]};const per={};const widths=[];
for(const d of days){per[d]={dawn:[0,0],h2:[0,0]};
  for(const [key,[lo,hi]] of RG){if(!key.startsWith(d))continue;const m=+key.split(' ')[1];if(m<420||m>1380)continue;const w=hi-lo;widths.push(w);
    for(const [k,f] of [['dawn',D[d].cb(m)],['h2',fc(d,m)]]){if(f==null)continue;const inR=f>=lo&&f<=hi, in1=f>=lo-w&&f<=hi+w;
      res[k][0]+=inR;res[k][1]+=in1;res[k][2]++;res[k][3]+=Math.abs(f-(lo+hi)/2)/((lo+hi)/2);per[d][k][0]+=inR;per[d][k][1]++;}}}
const pc=(a,b)=>(100*a/b).toFixed(1);
console.log('서울시 범위 폭(07~23시): 중앙 '+widths.sort((a,b)=>a-b)[widths.length>>1]+'명, 최소 '+widths[0]+', 최대 '+widths[widths.length-1]);
for(const [k,lab] of [['dawn','새벽 예상'],['h2','2시간 앞']]){const r=res[k];
  console.log(lab+': 범위 안 '+pc(r[0],r[2])+'% | 범위 한 칸 넓혀서 '+pc(r[1],r[2])+'% | 범위 가운데와의 평균 차이 '+(100*r[3]/r[2]).toFixed(1)+'% | '+r[2]+'개 시각 | 날마다 범위 안: '+days.map(d=>d.slice(5)+' '+pc(per[d][k][0],per[d][k][1])+'%').join(', '));}
