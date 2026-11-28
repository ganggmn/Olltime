<script>
(async()=>{
__DATA__
/* 역과 노선 이름의 가운뎃점은 화면에 쓰지 않아요 */
ROUTE.ln=ROUTE.ln.map(l=>l.replace(/·/g,''));ROUTE.st.forEach(s=>{s[0]=s[0].replace(/·/g,' ')});

const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const RM=matchMedia('(prefers-reduced-motion: reduce)');
const ONLY=document.documentElement.classList.contains('only-story');
const smooth=()=>RM.matches?'auto':'smooth';
const W7='일월화수목금토';
const dayLabel=d=>{const x=new Date(d+'T12:00:00+09:00');return`${x.getUTCMonth()+1}월 ${x.getUTCDate()}일 ${W7[x.getUTCDay()]}요일`};
const mdLabel=d=>dayLabel(d).replace(/ \S+요일$/,'');
/* 혼잡 단계: 무채색에서 빨강으로. 붐빌수록 진하고 붉게 */
/* 혼잡 막대: 여유·보통은 색 없이, 약간 혼잡은 노랑, 혼잡은 빨강 (각 원색 70%를 흰 바탕에 얹은 값) */
const LVG={'여유':'#EEEEF0','보통':'#A1A1AA','약간 혼잡':'#FFD64D','혼잡':'#E76767'},LVN={'여유':0,'보통':1,'약간 혼잡':2,'혼잡':3};
const LVC=l=>'lv-'+(l==='약간 혼잡'?'약간':l);
const HATCH=c=>`repeating-linear-gradient(45deg,${c} 0 2.5px,#FFFFFF 2.5px 4px)`;
const C_IN='#A1A1AA',C_SHOW='#D9D9DE',C_OUT='#E76767';
/* 출입문 원: 10분에 나가는 차가 남2문 최대 124대 대비 얼마인지 */
const GQ={'북2문':[47,75,104],'동2문':[47,77,103],'남2문':[29,65,132],'서2문':[16,52,101]}; /* 2025년 1~7월, 10분 동안 나간 차: 상위 10%, 상위 1%, 최대 */
const gateC=(n,v)=>{const q=GQ[n];return!q||v<q[0]?'#A1A1AA':v<q[1]?'#FFD64D':'#E76767'};
const ic=(n,extra='')=>`<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"${extra}>${ICONS[n]||''}</svg>`;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const hm=m=>{m=((Math.round(m)%1440)+1440)%1440;return String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0')};
const hmT=m=>(m>=1440?'다음 날 ':'')+hm(m);
const hmN=m=>(m>=1440?'<span class="nd">다음 날</span>':'')+hm(m);
const hmX=m=>m>=1440&&m<1800?String(Math.floor(m/60)).padStart(2,'0')+':'+String(Math.round(m)%60).padStart(2,'0'):hm(m);
const rng=(a,b)=>`${hm(a)}–${hmX(b<a?b+1440:b)}`;
const hourTxt=m=>(m>=1440?'내일 ':'')+Math.floor((m%1440)/60)+'시';
const toM=t=>{const[a,b]=t.split(':').map(Number);return a*60+b};
const num=n=>Math.round(n).toLocaleString('ko-KR');
const kst=()=>{const d=new Date(Date.now()+9*36e5);return{date:d.toISOString().slice(0,10),m:d.getUTCHours()*60+d.getUTCMinutes()}};
const getJSON=async(u,ms)=>{const c=new AbortController(),t=setTimeout(()=>c.abort(),ms);try{const r=await fetch(u,{signal:c.signal});if(!r.ok)throw new Error(String(r.status));return await r.json()}finally{clearTimeout(t)}};
/* 공연 일정: 올림픽공원 홈페이지에서 읽어 온 것을 적어 둔 목록에 더함(같은 공연장·같은 시각이면 적어 둔 것을 둠, 시각이 바뀌었으면 홈페이지 것으로). 못 받으면 적어 둔 목록 그대로 */
let SHOWSRC='';
const mergeShows=list=>{const yr=kst().date.slice(0,4),lab=d=>(d.slice(0,4)!==yr?d.slice(0,4)+'년 ':'')+dayLabel(d);let n=0;
 for(const g of list||[]){if(!g||!/^\d{4}-\d{2}-\d{2}$/.test(g.d)||!/^\d{2}:\d{2}$/.test(g.t)||!VENOK.has(g.venue))continue;
  if(SHOWS.some(s=>s.d===g.d&&s.venue===g.venue&&s.t===g.t))continue;
  const same=SHOWS.filter(s=>s.d===g.d&&s.venue===g.venue),ng=list.filter(x=>x.d===g.d&&x.venue===g.venue).length;
  if(same.length===1&&ng===1){same[0].t=g.t;if(g.run)same[0].run=g.run}
  else SHOWS.push({d:g.d,day:lab(g.d),t:g.t,name:g.name,short:g.short||g.name,venue:g.venue,run:g.run||null});n++}
 SHOWS.sort((a,b)=>a.d<b.d?-1:a.d>b.d?1:a.t<b.t?-1:a.t>b.t?1:0);return n};
const VENOK=new Set(['KSPO DOME','올림픽홀','핸드볼경기장']);
if(!ONLY)try{const j=await getJSON('/api/shows',1500);if(j&&j.ok&&Array.isArray(j.list)){mergeShows(j.list);SHOWSRC=j.read_at||''}}catch(e){}
const EXITP50=45; /* 2025년 큰 공연 28일: 공연 뒤 나가는 차의 절반이 빠진 때는 시작 195분 뒤(러닝타임 150분이면 끝나고 45분 뒤), 90%는 끝나고 110분 뒤 */

/* 상태: 서울시 데이터를 기다리는 중(pending), 받음(live), 못 받음(fail) */
let STATE='pending',CITY,PARK=null,N,NOWM,TODAY,NEXTD,todayShows,VIEW=null,viewShows,TREF,T=300,userT=false;
const blankCity=()=>{const k=kst();return{now:{time:k.date+' '+hm(k.m),m:k.m,lvl:null,lo:null,hi:null,temp:null,ptype:'없음',pcp:'',air:''},actual:[],fcst:[]}};
const pred=s=>{const st=toM(s.t),run=s.run||150;return{st,run,assumed:!s.run,inA:st-160,inPk:st-90,inB:st-30,end:st+run,outA:st+run+20,outPk:st+run+50,outB:st+run+110}};
const runTxt=p=>p.assumed?'150분 가정 (미공지)':`${p.run}분`;
const REFNAME={sat:'작년 12월 6일 공연 날 기록',fri:'작년 12월 5일 공연 날 기록',base:'작년 공연 없는 평일 평균'};
const refFor=s=>{if(!s)return{r:REF.base,shift:0,key:'base'};const st=toM(s.t),key=st>=1170?'fri':'sat',r=REF[key];return{r,shift:st-r.start,key}};
const refAt=(ref,t)=>{const tt=Math.max(300,Math.min(1560,t-ref.shift));const rows=ref.r.rows;return rows[Math.max(0,Math.min(rows.length-1,Math.round((tt-300)/10)))]};
const setView=v=>{VIEW=v;viewShows=SHOWS.filter(s=>s.d===VIEW);TREF=refFor(viewShows[0])};
/* NOWM: 서울시가 측정한 시각(30분쯤 늦어요). nowC(): 실제 지금 시각. 출발 시각과 '지금' 표시는 실제 시각을 써요 */
const nowC=()=>{const k=kst();return Math.max(NOWM,k.date===TODAY?k.m:k.date>TODAY?k.m+1440:k.m)};
const NLV=l=>l==='붐빔'?'혼잡':l==='약간 붐빔'?'약간 혼잡':l;
const derive=()=>{if(CITY.now&&CITY.now.lvl)CITY.now.lvl=NLV(CITY.now.lvl);(CITY.fcst||[]).forEach(f=>{f[3]=NLV(f[3])});N=CITY.now;NOWM=N.m;TODAY=N.time.slice(0,10);todayShows=SHOWS.filter(s=>s.d===TODAY);NEXTD=(SHOWS.find(s=>s.d>TODAY)||{}).d||null;
 setView(VIEW&&VIEW===NEXTD&&!todayShows.length?VIEW:TODAY)};
/* 같은 날 공연이 여러 개면 그 시각에 가장 가까운 공연을 보여줘요 */
const showAt=t=>{if(!viewShows.length)return null;const on=viewShows.filter(s=>{const p=pred(s);return t>=p.inA-60&&t<p.outB});if(on.length)return on.find(s=>s.venue==='KSPO DOME')||on[on.length-1];const nx=viewShows.find(s=>pred(s).inA-60>t);return nx||viewShows[viewShows.length-1]};
const OCCMAX=Math.max(...REF.sat.rows.map(r=>r[1]),...REF.fri.rows.map(r=>r[1]));
/* 공원 안 인구: 서울시가 낸 값(500명 단위 구간)만 그대로 써요. 실측 사이나 예보 사이를 이어 붙이지 않아요 */
const people=t=>{if(VIEW!==TODAY)return{none:'preview'};if(STATE!=='live')return{none:STATE};
 if(Math.abs(t-NOWM)<=5)return{lo:N.lo,hi:N.hi,lvl:N.lvl,src:'실측',at:NOWM};
 if(t<=NOWM){const A=CITY.actual.length>1||!PP.length?CITY.actual:PP.filter(r=>r[0]<NOWM).concat(CITY.actual);if(!A.length||t<A[0][0]-10)return{none:'before',at:A.length?A[0][0]:NOWM};let a=A[0];for(const x of A)if(x[0]<=t)a=x;return{lo:a[1],hi:a[2],lvl:a[3],src:'실측',at:a[0]}}
 const pts=[[NOWM,N.lo,N.hi,N.lvl,'실측'],...CITY.fcst.map(f=>[f[0],f[1],f[2],f[3],'예보'])],last=pts[pts.length-1];
 if(t>last[0]+30)return{none:'after',at:last[0]};
 let b=pts[0];for(const p of pts)if(Math.abs(p[0]-t)<Math.abs(b[0]-t))b=p;return{lo:b[1],hi:b[2],lvl:b[3],src:b[4],at:b[0]}};
const syncTxt=m=>`최신 동기화 : ${Math.floor((m%1440)/60)}시 ${m%60}분`;
/* 공연 뒤 출차: 공연 전에 고정한 확률표(EXITS, 출차 시작 80% 범위)가 있으면 그것, 없으면 2025년 기록 평균(pred) */
const exitOf=s=>{const x=EXITS[s.d+' '+s.t];if(x)return{lbl:'출차 시작',a:x[0],b:x[1],p:'80%'};const p=pred(s);return{lbl:'출차 몰림',a:p.outA,b:p.outB,p:'예상'}};

/* 아이콘 채우기 */
$$('i[data-ic]').forEach(n=>{n.outerHTML=ic(n.dataset.ic,n.id?` id="${n.id}"`:'')});

/* 머리글 */
let FLOORP=1030,FLOORD=false,PT=[],PP=[];const PCAP0=2200;
const renderHero=()=>{const live=STATE==='live',pend=STATE==='pending';
 $('#now').setAttribute('aria-busy',String(pend));
 $('#stamp').textContent=live?syncTxt(NOWM):pend?'동기화 중':'동기화 실패';
 $('#ftStamp').textContent=live?`서울시 측정 ${hm(NOWM)} · 공개 = 측정 + 30분`:pend?'동기화 중':'서울시 연결 안 됨 · 공연 예상 = 2025 주차 기록';
 $('#heroCap').innerHTML=esc(dayLabel(TODAY))+(live?`<span class="mob"> · ${syncTxt(NOWM)}</span>`:pend?'':' · 서울시 연결 안 됨');
 $('#heroH').innerHTML=live?`지금 <span class="${LVC(N.lvl)}">${esc(N.lvl)}</span>`:pend?'불러오는 중':'연결 안 됨';
 const S=todayShows;
 $('#heroLead').textContent=live?`${num(N.lo)}~${num(N.hi)}명`:'';
 const r=$('#retry');r.hidden=live||(pend&&!r.dataset.busy);r.disabled=pend;r.textContent=pend?'불러오는 중':'다시 불러오기';
 const ph='<span class="ph"></span>',PCAP=2200,plv=v=>{const r=v/PCAP;return r>=.9?['만차','var(--bad)']:r>=.7?['혼잡','var(--warn)']:r>=.5?['다소 혼잡','']:['여유','']},fl=Math.round(FLOORP);
 const park=PARK?(([l,c])=>`<span><span style="font-weight:600${c?';color:'+c:''}">${l}</span> ${num(PARK.sum)} / ${num(PCAP)}대</span><details class="fx"><summary>장기 제외 ${num(Math.max(0,PARK.sum-fl))}대</summary><span class="cap">= ${num(PARK.sum)} − ${num(fl)} (새벽 2–5시 중앙값)</span></details>`)(plv(PARK.sum)):pend?ph:'연결 안 됨';
 const wx=()=>`${N.temp}도`+(N.ptype&&N.ptype!=='없음'?` · ${N.ptype}`:'')+(N.air?` · 미세먼지 ${N.air}`:'');
 const rows=live?[['주차장',park],['날씨',wx()]]:pend?[['주차장',park],['날씨',ph]]:[['주차장',park],['날씨','연결 안 됨']];
 $('#facts').innerHTML=rows.map(([a,b])=>`<div><dt>${a}</dt><dd>${b}</dd></div>`).join('');
 const SH=S.length?S:NEXTD?SHOWS.filter(s=>s.d===NEXTD):[];
 if(!SH.length){$('#today').innerHTML='';return}
 const isToday=SH[0].d===TODAY;
 $('#today').innerHTML=`<h2 class="h-sub">${isToday?'오늘 공연':'다음 공연 · '+esc(SH[0].day)}</h2><ul class="shl x">${SH.map(s=>{const p=pred(s),x=exitOf(s);return`<li><span class="t">${s.t}</span><span>${esc(s.name)}<span class="cap">${esc(s.venue)} · ${s.run?`${s.t}–${hm(p.end)} (${s.run}분)`:'종료 미정'}</span></span><span class="xo"><span class="cap">${x.lbl}</span><b>${rng(x.a,x.b)}</b><span class="cap">${x.p}</span></span></li>`}).join('')}</ul><p class="cap">출처: 올림픽공원 공연 일정</p>`};

/* 지도 */
const svg=$('#svg'),dyn=$('#dyn');
const halo='paint-order:stroke;stroke:#FAFAFA;stroke-width:4px;stroke-linejoin:round';
/* 좌표 = OpenStreetMap 경도·위도를 지도 단위로 옮긴 값 (1단위 ≈ 1.8m). 출입문: 북2·동2·남2·남4·서1 = 이름 확인, 나머지 = 길과 공원 경계가 만나는 곳 */
const VEN={'KSPO DOME':[760,402,37],'올림픽홀':[766,677,22],'핸드볼경기장':[708,517,29]};
const GATES=[['북1문',256,95],['북2문',780,129,3],['동1문',947,522],['동2문',902,607,4],['남1문',778,822],['남2문',534,706,5],['남3문',323,612],['서1문',129,360],['서2문',196,221,6]];
const LOTS=[[771,331],[829,590],[602,666],[198,264],[668,648],[739,542]];
/* 역: [이름, 노선 번호들, 덧붙일 말, x, y] */
const STN=[['올림픽공원역',[5,9],'',925,590],['한성백제역',[9],'남4문 앞',213,560],['몽촌토성역',[8],'',41,506]];
const LC={5:'#996CAC',8:'#E6186C',9:'#BDB092'};
const PL=[['KSPO DOME',760,402,37,0],['몽촌토성',420,340,0,0,'c'],['올림픽홀',766,677,22,1],['티켓링크 라이브 아레나',708,517,29,1],['우리금융아트홀',645,552,24,1],['한성백제박물관',432,633,22,1],['88호수',660,245,0,1,'c'],['몽촌해자',292,364,0,1,'c'],['88잔디마당',640,418,0,1,'c'],['세계평화의문',173,458,12,1],['올림픽수영장',712,300,30,2],['벨로드롬',559,544,28,2],['테니스경기장',805,634,22,2],['소마미술관',303,546,14,2],['올림픽기념관',181,335,16,2],['파크텔',229,222,14,2],['몽촌역사관',603,121,12,2],['나홀로나무',415,188,4,2],['장미광장',766,788,0,2,'c'],['성내천',300,112,0,2,'c']];
const ROADS=[['올림픽로',150,228],['위례성대로',356,676],['양재대로',908,700],['강동대로',880,160]];
let K=.57;
const gIc=(n,x,y,u)=>`<rect x="${(x-11*u).toFixed(1)}" y="${(y-11*u).toFixed(1)}" width="${(22*u).toFixed(1)}" height="${(22*u).toFixed(1)}" rx="${(3*u).toFixed(1)}" fill="#FFFFFF" stroke="#D4D4D8" stroke-width="${(.8*u).toFixed(2)}"/><g transform="translate(${(x-8*u).toFixed(1)} ${(y-8*u).toFixed(1)}) scale(${(.6667*u).toFixed(4)})" fill="none" stroke="#0A0A0A" stroke-width="2.625" stroke-linecap="round" stroke-linejoin="round">${ICONS[n]}</g>`;
const venueState=(p,t)=>{if(!p)return'';if(t<p.inA-60)return'';if(t<p.inA)return'관객 도착 시작';if(t<=p.inB)return'입차 몰림';if(t<p.st)return'입장';if(t<p.end)return'공연 중';if(t<p.outA)return'퇴장 시작';if(t<p.outB)return Math.abs(t-p.outPk)<=20?'출차 최대':'출차 몰림';return''};
/* 글자 폭 어림 (지도 단위): 한글 1em, 숫자 .6em, 나머지 .62em */
const twd=(s,f)=>{let w=0;for(const ch of String(s))w+=/[가-힣]/.test(ch)?f*.98:/[0-9]/.test(ch)?f*.6:ch===' '?f*.3:f*.62;return w};
/* 라벨끼리, 라벨과 아이콘이 겹치지 않게: 후보 자리 중 빈 곳에 놓고, 없으면 꼭 필요한 라벨만 가장 덜 겹치는 곳에 */
const drawMap=()=>{const u=1/K,f=13*u,fs=f.toFixed(2),hs=`paint-order:stroke;stroke:#FFFFFF;stroke-width:${(4*u).toFixed(2)}px;stroke-linejoin:round`;
 const occ=[],box=(x0,y0,x1,y1)=>occ.push([x0,y0,x1,y1]),isx=(r,q)=>Math.max(0,Math.min(r[2],q[2])-Math.max(r[0],q[0]))*Math.max(0,Math.min(r[3],q[3])-Math.max(r[1],q[1]));
 /* 화면 밖으로 나가는 부분은 겹침보다 무겁게 셈 */
 const VW=[vb.x+4*u,vb.y+4*u,vb.x+vb.w-4*u,vb.y+vb.h-4*u],ov=r=>occ.reduce((a,q)=>a+isx(r,q),0)+10*((r[2]-r[0])*(r[3]-r[1])-isx(r,VW));
 {const c=$('.mapctl'),sr=svg.getBoundingClientRect();if(c&&sr.width){const q=c.getBoundingClientRect(),X=px=>vb.x+(px-sr.left)*u,Y=py=>vb.y+(py-sr.top)*u;box(X(q.left)-4*u,Y(q.top)-4*u,X(q.right)+4*u,Y(q.bottom)+4*u)}}
 const tx=(x,y,str,o={})=>`<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" font-size="${o.f?o.f.toFixed(2):fs}" text-anchor="${o.a||'middle'}"${o.w?' font-weight="600"':''} fill="${o.c||'#0A0A0A'}" style="${hs}">${str}</text>`;
 const rectOf=(x,y,w,a,ff=f)=>{const x0=a==='start'?x:a==='end'?x-w:x-w/2;return[x0-2*u,y-ff*.82,x0+w+2*u,y+ff*.28]};
 /* lines: [[문자열,{w,c}],...] 두 줄까지. cands: [x,y,anchor] */
 /* 노선 타원: 열차 목록과 같은 모양(번호 크게, '호선' 작게) */
 const p1=n=>12*u+twd(n,12*u)+twd('호선',9.5*u)+u,pw=ps=>ps.reduce((a,n)=>a+p1(n),0)+(ps.length-1)*4*u;
 const lw=([s,o])=>o.p?pw(o.p)+(s?6*u+twd(s,f):0):twd(s,f);
 const pillRow=(x0,y,ps,s)=>{let cx=x0,o='';const cy=y-f*.35;for(const n of ps){const w=p1(n);o+=`<rect x="${cx.toFixed(1)}" y="${(cy-9*u).toFixed(1)}" width="${w.toFixed(1)}" height="${(18*u).toFixed(1)}" rx="${(9*u).toFixed(1)}" fill="${LC[n]||'#0A0A0A'}" stroke="#FFFFFF" stroke-width="${(1.5*u).toFixed(2)}"/><text x="${(cx+6*u).toFixed(1)}" y="${(cy+4.3*u).toFixed(1)}" font-size="${(12*u).toFixed(2)}" font-weight="600" fill="${n===9?'#0A0A0A':'#FFFFFF'}">${n}<tspan font-size="${(9.5*u).toFixed(2)}" dx="${u.toFixed(2)}">호선</tspan></text>`;cx+=w+4*u}
  if(s)o+=tx(cx+2*u,y,s,{a:'start',c:'#6B6B74'});return o};
 const place=(lines,cands,must)=>{const ww=Math.max(...lines.map(lw)),pp=lines.some(([,o])=>o.p)?2*u:0,hh=(lines.length-1)*f*1.2+pp;let best=null,bo=Infinity;
  for(const[x,y0,a,up]of cands){const y=up?y0-hh:y0,r=rectOf(x,y,ww,a);r[3]+=hh;const o=ov(r);if(o===0){best=[x,y,a,r];bo=0;break}if(o<bo){bo=o;best=[x,y,a,r]}}
  if(!best||(bo>0&&!must))return'';const[x,y,a,r]=best;occ.push(r);return lines.map(([s,o],i)=>{const yy=y+i*f*1.2;if(!o.p)return tx(x,yy,s,{a,...o});const w=lw([s,o]);return pillRow(a==='start'?x:a==='end'?x-w:x-w/2,yy+pp,o.p,s)}).join('')};
 /* 넷째 값 1 = 위쪽 자리: 두 줄 라벨은 줄 수만큼 위로 올려서 아이콘을 덮지 않게 */
 const around=(x,y,d)=>[[x+d+5*u,y+f*.35,'start'],[x-d-5*u,y+f*.35,'end'],[x,y-d-5*u,'middle',1],[x,y+d+f+2*u,'middle'],[x+d*.7+4*u,y-d*.7-3*u,'start',1],[x-d*.7-4*u,y-d*.7-3*u,'end',1],[x+d*.7+4*u,y+d*.7+f,'start'],[x-d*.7-4*u,y+d*.7+f,'end']];
 const sh=showAt(T),p=sh?pred(sh):null,row=refAt(TREF,T);let g='',lab='';
 /* 1. 그림 먼저: 공연장 원, 출입문 점·출차 원, 주차·역 아이콘. 자리도 미리 차지 */
 let V=null;if(sh){const[vx,vy,vr]=VEN[sh.venue]||VEN['KSPO DOME'];const live=T>=p.inA-60&&T<p.outB;V=[vx,vy,vr];
  g+=`<circle cx="${vx}" cy="${vy}" r="${vr}" fill="${live?'#0A0A0A':'#FFFFFF'}" stroke="#0A0A0A" stroke-width="${(1.5*u).toFixed(2)}"/>`;box(vx-vr,vy-vr,vx+vr,vy+vr)}
 const GB=[];for(const[n,x,y,k]of GATES){g+=`<circle cx="${x}" cy="${y}" r="${(3*u).toFixed(1)}" fill="#0A0A0A"/>`;box(x-4*u,y-4*u,x+4*u,y+4*u);
  if(k){const v=row[k],r=Math.min(1,v/(GQ[n]?GQ[n][2]:124)),c=gateC(n,v),rr=(7+r*17)*u;GB.push([n,x,y,rr,v]);
   g+=`<circle class="gp" style="animation-delay:-${((Date.now()%1600)/1000).toFixed(2)}s" cx="${x}" cy="${y}" r="${rr.toFixed(1)}" fill="${c}" fill-opacity=".3"/>`}}
 for(const[x,y]of LOTS){g+=gIc('square-parking',x,y,u*.85);box(x-10*u,y-10*u,x+10*u,y+10*u)}
 for(const[n,ls,ss,x,y]of STN){g+=gIc('train-front',x,y,u);box(x-12*u,y-12*u,x+12*u,y+12*u)}
 /* 2. 꼭 보여야 하는 라벨: 지금 공연, 출차 수가 있는 문, 역 */
 if(V){const[vx,vy,vr]=V,st=venueState(p,T),L=[[`${esc(sh.venue)} · ${sh.t} ${esc(sh.short)}`,{w:1}]];if(st)L.push([st,{}]);lab+=place(L,around(vx,vy,vr),true)}
 for(const[n,x,y,rr,v]of GB)lab+=place([[`${n} ${Math.round(v)}대`,{w:1}]],around(x,y,Math.max(rr*.55,6*u)),true);
 for(const[n,ls,ss,x,y]of STN)lab+=place(K>=.6?[[n,{w:1}],[ss,{p:ls}]]:[[n,{w:1}]],around(x,y,12*u),true);
 /* 3. 시설: 확대할수록 더. 자리가 없으면 생략 */
 const tierOK=t=>t===0||(t===1&&K>=.3)||(t===2&&K>=.55);
 for(const[n,x,y,d,t,pos]of PL){if(!tierOK(t)||(sh&&n===sh.venue)||(sh&&sh.venue==='핸드볼경기장'&&n==='티켓링크 라이브 아레나'))continue;const c=t===0?'#0A0A0A':'#52525B';
  lab+=place([[n,{c,w:t===0}]],pos==='c'?[[x,y+f*.35,'middle'],[x,y-f*.6,'middle'],[x,y+f*1.3,'middle']]:around(x,y,d),false)}
 if(K>=.33)for(const[n,x,y,k]of GATES)if(!k)lab+=place([[n,{c:'#6B6B74'}]],around(x,y,4*u),false);
 if(K>=.45)for(const[n,x,y]of ROADS)lab+=place([[n,{c:'#A1A1AA'}]],[[x,y,'middle']],false);
 dyn.innerHTML=g+lab};
const BB={x:30,y:8,w:950,h:830};let vb={x:0,y:0,w:1000,h:860};
const setVB=()=>{svg.setAttribute('viewBox',`${vb.x.toFixed(1)} ${vb.y.toFixed(1)} ${vb.w.toFixed(1)} ${vb.h.toFixed(1)}`);const r=svg.getBoundingClientRect(),k=r.width?Math.min(r.width/vb.w,r.height/vb.h):0;if(k&&Math.abs(k-K)>.002){K=k;drawMap()}};
const fit=()=>{const m=$('#map'),W=m.clientWidth,H=m.clientHeight;if(!W||!H)return;const pad=12,top=W<560?52:0,fw=W-pad*2-(W<560?0:52),fh=H-pad*2-top;const s=Math.min(fw/BB.w,fh/BB.h);vb.w=W/s;vb.h=H/s;vb.x=BB.x-pad/s-(fw/s-BB.w)/2;vb.y=BB.y-(pad+top)/s-(fh/s-BB.h)/2;setVB()};
const zoom=f=>{const m=$('#map'),ar=(m.clientHeight/m.clientWidth)||.72,cx=vb.x+vb.w/2,cy=vb.y+vb.h/2;vb.w=Math.max(260,Math.min(2600,vb.w*f));vb.h=vb.w*ar;vb.x=cx-vb.w/2;vb.y=cy-vb.h/2;setVB()};
$('#zin').onclick=()=>zoom(.8);$('#zout').onclick=()=>zoom(1.25);$('#zre').onclick=fit;
new ResizeObserver(fit).observe($('#map'));
{const m=$('#map');let d=null;m.addEventListener('pointerdown',e=>{if(e.button!==0)return;d={x:e.clientX,y:e.clientY,vx:vb.x,vy:vb.y};m.classList.add('drag');m.setPointerCapture(e.pointerId)});
 m.addEventListener('pointermove',e=>{if(!d)return;const r=svg.getBoundingClientRect(),s=Math.max(vb.w/r.width,vb.h/r.height);vb.x=d.vx-(e.clientX-d.x)*s;vb.y=d.vy-(e.clientY-d.y)*s;setVB()});
 const up=()=>{d=null;m.classList.remove('drag')};m.addEventListener('pointerup',up);m.addEventListener('pointercancel',up)}

/* 지표 */
const NONE={pending:['불러오는 중','서울시 데이터를 기다려요'],fail:['알 수 없어요','서울시 데이터를 불러오지 못했어요'],preview:['예보 전','서울시 예보는 12시간 후까지만 나와요']};
const drawMetrics=()=>{const pp=people(T),row=refAt(TREF,T),sh=showAt(T),p=sh?pred(sh):null,st=venueState(p,T);
 const gs=[['북2문',row[3]],['동2문',row[4]],['남2문',row[5]],['서2문',row[6]]];
 const lbl1=VIEW!==TODAY?`${mdLabel(VIEW)} 미리 보기`:Math.abs(T-nowC())<10?'지금':T<nowC()?'지난 시각':'앞으로';
 let ppl,cong;if(!pp.none){cong=`<p class="v big ${LVC(pp.lvl)}">${pp.lvl}</p><p class="cap">서울시 ${hmT(pp.at)} ${pp.src}</p>`;ppl=`<p class="v">${num(pp.lo)}~<wbr>${num(pp.hi)}명</p><p class="cap">서울시 발표 범위</p>`}
 else{const M=NONE[pp.none]||(pp.none==='before'?['기록 없음',`서울시 실측은 ${hm(pp.at)}부터 있어요`]:['예보 없음',CITY.fcst.length?`서울시 예보는 ${hmT(pp.at)}까지예요`:'서울시가 예보를 내지 않았어요']);cong=`<p class="v big" style="color:var(--ink-2)">${M[0]}</p><p class="cap">${M[1]}</p>`;ppl=`<p class="v">-</p><p class="cap">서울시 값이 없어요</p>`}
 $('#metrics').innerHTML=`<div class="mt wide"><p class="lbl">출구별 출차 (대/10분, 예상) · ${VIEW!==TODAY?mdLabel(VIEW)+' ':''}${hmT(T)}${st?' · '+esc(st):''}</p><div class="gts">${gs.map(([n,v])=>`<div><span>${n}</span><span class="bar"><i style="width:${Math.min(1,v/(GQ[n]?GQ[n][2]:124))*100}%;background:${gateC(n,v)==='#A1A1AA'?'':gateC(n,v)}"></i><b></b></span><span>${Math.round(v)}</span></div>`).join('')}</div></div>`};
const sayT=()=>{const pp=people(T),sh=showAt(T),st=venueState(sh?pred(sh):null,T),row=refAt(TREF,T);
 $('#srT').textContent=`${VIEW!==TODAY?mdLabel(VIEW)+' ':''}${hmT(T)}. `+(st?`${sh.venue} ${st}. `:'')+(pp.none?'':`공원 안 ${num(pp.lo)}에서 ${num(pp.hi)}명, ${pp.lvl}. `)+`주차장 안 차량 약 ${num(row[1])}대 예상.`};

/* 시간 막대 */
const tr=$('#tr'),X0=300,X1=1560,pct=m=>(m-X0)/(X1-X0)*100;
const segs=list=>{const out=[];for(const s of list){const l=out[out.length-1];if(l&&l[2]===s[2])l[1]=s[1];else out.push([...s])}return out.map(([a,b,bg])=>`<span style="width:${(b-a)/(X1-X0)*100}%;background:${bg}"></span>`).join('')};
let PKB=[];
const SW=(bg,t)=>`<span><i style="background:${bg}"></i>${t}</span>`;
const MAPLEG='<span><i style="background:#A1A1AA"></i>원 클수록 출차 많음 (대/10분, 예상)</span><span><i style="background:#FFD64D"></i>문별 상위 10%</span><span><i style="background:#E76767"></i>상위 1%</span><span>지도 © OpenStreetMap 기여자</span>';
const renderView=reset=>{
 const sw=$('#vsw');if(!todayShows.length&&NEXTD){sw.hidden=false;sw.innerHTML=[[TODAY,'오늘'],[NEXTD,`${mdLabel(NEXTD)} 공연 날 미리 보기`]].map(([d,t])=>`<button type="button" data-v="${d}" aria-pressed="${VIEW===d}">${t}</button>`).join('')}else sw.hidden=true;
 const st=$('#strip'),X=VIEW===TODAY?viewShows.map(exitOf):[];
 if(VIEW===TODAY){
  /* 1시간 = 1칸. 칸 색 = 그 1시간 안 서울시 값 중 가장 높은 단계 */
  const cells=[];for(let h=X0;h<X1;h+=60){let v=-1;for(let t=h+5;t<h+60;t+=10){const pp=people(t);if(!pp.none)v=Math.max(v,LVN[pp.lvl])}cells.push(v)}
  const LVK=['여유','보통','약간 혼잡','혼잡'];
  st.className='strip cells';st.innerHTML=cells.map((v,k)=>`<span${v<0?' class="na"':` style="background:${LVG[LVK[v]]}"`} title="${hm(X0+k*60)}–${hmX(X0+k*60+60)} ${v<0?'자료 없음':LVK[v]}"></span>`).join('');
  const used=new Set(cells);
  /* 만차 괄호 (주차 2,200대의 90% 이상 = 주차장 칸의 '만차'와 같은 기준)
     실선 = 실측(오늘 5분 기록), 점선·오른쪽 열림 = 예상(지금 대수 + 2025 같은 유형 공연 날 입차 − 출차 누적) */
  const nw=nowC(),TH=2200*.9,act=PT.filter(r=>r[0]<=nw).concat(PARK?[[nw,PARK.sum]]:[]).sort((a,b)=>a[0]-b[0]),IV=[];let cur=null;
  for(const[m,v]of act)if(v>=TH){if(cur&&m-cur[1]<=20)cur[1]=m;else{cur=[m,m];IV.push(cur)}}
  let PI=null;if(PARK){let occ=PARK.sum,a=occ>=TH?nw:null,b=a;for(let t=Math.ceil(nw/10)*10;t<X1;t+=10){const r=refAt(TREF,t);occ+=r[2]-(r[3]+r[4]+r[5]+r[6]+r[7]);if(occ>=TH){if(a==null)a=t+10;b=t+10}else if(a!=null)break}if(a!=null&&b>a)PI=[a,b]}
  /* 주차 칸: 2,200대 대비 < 50% 여유 · ≥ 50% 보통 · ≥ 70% 약간 혼잡 · ≥ 90% 만차(빨강). 지난 시간 = 실측 최고, 이후 = 예상(점선) */
  const PS=v=>{const r=v/2200;return r>=.9?3:r>=.7?2:r>=.5?1:0},pr={};
  if(PARK){let occ=PARK.sum;for(let t=Math.ceil(nw/10)*10;t<X1;t+=10){const r=refAt(TREF,t);occ+=r[2]-(r[3]+r[4]+r[5]+r[6]+r[7]);pr[t+10]=occ}}
  const PC=[];for(let h=X0;h<X1;h+=60){const a=act.filter(r=>r[0]>=h&&r[0]<h+60);if(a.length){PC.push([PS(Math.max(...a.map(r=>r[1]))),0]);continue}const q=Object.keys(pr).map(Number).filter(t=>t>h&&t<=h+60);PC.push(q.length?[PS(Math.max(...q.map(t=>pr[t]))),1]:[-1,0])}
  const PNM=['여유','보통','약간 혼잡','만차'];
  $('#strip2').innerHTML=PC.map(([v,e],k)=>`<span class="${v<0?'na':e?'pd p'+v:'p'+v}" title="${hm(X0+k*60)}–${hmX(X0+k*60+60)} 주차 ${v<0?'자료 없음':PNM[v]+(e?' (예상)':'')}"></span>`).join('');
  if(PC.some(([v])=>v<0))used.add(-1);
  PKB=IV.filter(([a,b])=>b-a>=10).map(([a,b])=>[a,b,0,`만차 ${hm(a)}–${hm(b)}`]).concat(PI?[[PI[0],PI[1],1,`만차 예상 ${PI[0]<=nw+5?'~':hm(PI[0])+'–'}${hmX(PI[1])}`]]:[]);
  $('#sleg').innerHTML=`<span class="lh">인원 및 주차</span>`+SW(LVG['여유'],'여유')+SW(LVG['보통'],'보통')+SW(LVG['약간 혼잡'],'약간 혼잡')+SW(LVG['혼잡'],'혼잡·만차')+(used.has(-1)?'<span><i class="na"></i>자료 없음</span>':'')+'<span><i class="pd"></i>예상</span><span>인원 = 서울시 · 지금 이후 예보</span>';
  $('#mapleg').innerHTML=MAPLEG}
 else{const L=[],ps=viewShows.map(pred);for(let t=X0;t<X1;t+=10){const m=t+5;let bg='#FFFFFF';if(ps.some(p=>m>=p.st&&m<p.end))bg=C_SHOW;else if(ps.some(p=>m>=p.inA&&m<p.inB))bg=C_IN;else if(ps.some(p=>m>=p.outA&&m<p.outB))bg=C_OUT;L.push([t,t+10,bg])}
  st.className='strip';st.innerHTML=segs(L);PKB=[];$('#strip2').innerHTML='';
  $('#sleg').innerHTML=SW(C_IN,'입차 몰림')+SW(C_SHOW,'공연')+SW(C_OUT,'출차 몰림')+'<span>예상 · 2025 공연 날 기록</span>';
  $('#mapleg').innerHTML=MAPLEG}
 /* 공연 괄호: 이름 + 시작–끝. 끝 미정이면 오른쪽을 열어 둬요 */
 $('#shows').innerHTML=viewShows.map(s=>{const p=pred(s),b=Math.min(X1,p.end);return`<div class="sb${s.run?'':' open'}" style="left:${pct(p.st)}%;width:${pct(b)-pct(p.st)}%"><b>${esc(s.short||s.name)} ${s.t}${s.run?'–'+hmX(p.end):'~'}</b></div>`}).join('');
 $('#pk').innerHTML=PKB.map(([a,b,e,t])=>`<div class="pb${e?' open':''}" style="left:${pct(Math.max(X0,a))}%;width:${Math.max(.4,pct(Math.min(X1,b))-pct(Math.max(X0,a)))}%"><b>${t}</b></div>`).join('');
 placeShows();placePk();
 drawNow();
 $('#ticks').innerHTML=[360,540,720,900,1080,1260,1440].map(m=>`<span style="left:${pct(m)}%">${m===1440?'24시':m/60+'시'}</span>`).join('');
 tr.setAttribute('aria-label',VIEW===TODAY?'오늘 지도와 지표의 시각':`${mdLabel(VIEW)} 지도와 지표의 시각`);
 if(reset||!userT)T=VIEW===TODAY?nowC():viewShows.length?pred(viewShows[0]).inPk:900;setT(T)};
/* 괄호 이름이 겹치면 한 줄 위로, 오른쪽 끝을 넘으면 안으로 당겨요 */
const placeShows=()=>{const box=$('#shows'),W=box.clientWidth,rows=[];let top=0;
 for(const sb of box.querySelectorAll('.sb')){const b=sb.querySelector('b');b.style.transform='';const x0=sb.offsetLeft,bw=b.offsetWidth,dx=Math.max(0,x0+bw-W);if(dx)b.style.transform=`translateX(${-dx}px)`;
  const a=x0-dx,z=Math.max(x0+bw-dx,x0+sb.offsetWidth);let r=0;while(rows[r]&&rows[r].some(([p,q])=>a<q+12&&z>p-12))r++;(rows[r]=rows[r]||[]).push([a,z]);sb.style.bottom=r*24+'px';top=Math.max(top,r)}
 box.style.height=(24+top*24)+'px'};
new ResizeObserver(()=>placeShows()).observe($('#shows'));
/* 만차 괄호: 막대 아래. 이름이 겹치면 한 줄 아래로. 막대·만차 줄 높이에 맞춰 시각 막대 길이도 바꿔요 */
const placePk=()=>{const box=$('#pk'),W=box.clientWidth,rows=[];let n=0;
 for(const sb of box.querySelectorAll('.pb')){const b=sb.querySelector('b');b.style.transform='';const x0=sb.offsetLeft,bw=b.offsetWidth,dx=Math.max(0,x0+bw-W);if(dx)b.style.transform=`translateX(${-dx}px)`;
  const a=x0-dx,z=Math.max(x0+bw-dx,x0+sb.offsetWidth);let r=0;while(rows[r]&&rows[r].some(([p,q])=>a<q+12&&z>p-12))r++;(rows[r]=rows[r]||[]).push([a,z]);sb.style.top=r*24+'px';n=Math.max(n,r+1)}
 const two=VIEW===TODAY,base=two?38:14,h=n?base+6+n*24:base,trk=$('.track');trk.style.height=h+'px';box.style.top=(base+6)+'px';$('#nowmk').style.height=(base+6)+'px';tr.style.setProperty('--th',(h+6)+'px');tr.style.setProperty('--tl',(base+6)+'px');$('.rl').hidden=!two};
new ResizeObserver(()=>placePk()).observe($('#pk'));
const drawNow=()=>{const nm=$('#nowmk'),n=nowC();nm.hidden=VIEW!==TODAY||n<X0||n>X1;nm.style.left=pct(Math.min(X1,Math.max(X0,n)))+'%'};
/* 막대 아래 시각: 지금이면 '지금 15:40', 옮겼으면 그 시각 */
const drawTlab=()=>{const box=$('#tlab'),sp=box.firstElementChild,n=nowC(),at=VIEW===TODAY&&Math.abs(T-n)<10;sp.textContent=at?`지금 ${hm(n)}`:`${VIEW!==TODAY?mdLabel(VIEW)+' ':''}${hmT(T)}`;$('#nowmk').classList.toggle('dim',!at);sp.style.left=pct(T)+'%';sp.style.transform='translateX(-50%)';const W=box.clientWidth,x=box.clientWidth*pct(T)/100,w=sp.offsetWidth,dx=x-w/2<0?w/2-x:x+w/2>W?W-x-w/2:0;if(dx)sp.style.transform=`translateX(calc(-50% + ${dx}px))`};
new ResizeObserver(()=>drawTlab()).observe($('#tlab'));
const setT=t=>{T=Math.max(X0,Math.min(X1,Math.round(+t/10)*10));tr.value=T;tr.setAttribute('aria-valuetext',`${VIEW!==TODAY?mdLabel(VIEW)+' ':''}${hmT(T)}`);const tn=$('#tnow'),nw=nowC();if(tn)tn.hidden=!(VIEW===TODAY&&nw>=X0&&nw<=X1&&Math.abs(T-nw)>=10);drawTlab();drawMap();drawMetrics()};
$('#tnow').onclick=()=>{if(timer)stop();userT=false;setT(nowC());sayT()};
tr.addEventListener('input',()=>{userT=true;setT(tr.value)});tr.addEventListener('change',sayT);
$('#vsw').addEventListener('click',e=>{const b=e.target.closest('[data-v]');if(!b)return;setView(b.dataset.v);userT=false;renderView(true);const f=$(`#vsw [data-v="${VIEW}"]`);f&&f.focus();sayT()});
let timer=null;const playIcon=n=>{$('#play').innerHTML=ic(n)+(n==='play'?'하루 재생':'멈춤');$('#play').setAttribute('aria-label',n==='play'?'하루 흐름 재생':'멈춤')};
const stop=()=>{clearInterval(timer);timer=null;playIcon('play');sayT()};
$('#play').onclick=()=>{if(timer)return stop();userT=true;if(T>=X1)setT(X0);playIcon('pause');timer=setInterval(()=>{if(T>=X1)return stop();setT(T+10)},110)};

/* 공연 목록 */
const A0=13*60,A1=25*60,pc=m=>Math.max(0,Math.min(100,(m-A0)/(A1-A0)*100));
const axis=`<div class="tlax" aria-hidden="true">${[15,18,21,24].map(h=>`<span style="left:${pc(h*60)}%">${h}시</span>`).join('')}</div>`;

__TRAVEL__
const DEST={'KSPO DOME':[37.5192,127.1272],'올림픽홀':[37.5146,127.1268],'핸드볼경기장':[37.5170,127.1270],'park':[37.5185,127.1220]};
/* 노선 표시: 노선색 타원 안에 번호는 크게, '호선'은 작게 (서울시 공식 노선색) */
const lnPill=n=>`<i class="lp" data-l="${n}"><b>${n}</b><small>호선</small></i>`;
const lineP=l=>{const m=/^(\d)호선$/.exec(l);return m?lnPill(+m[1]):`<i class="lp"${l==='신분당선'?' data-l="sb"':''}>${esc(l.replace(/선$/,''))}</i>`};
const MODE={pt:['지하철','train-front'],car:['자동차','car'],bike:['따릉이','bike'],walk:['도보','footprints']};
const OPS=ROUTE.st.findIndex(s=>s[0]==='올림픽공원');
const jong=w=>{const c=w.charCodeAt(w.length-1)-0xAC00;return c>=0&&c<=11171?c%28:0};const iga=w=>w+(jong(w)?'이':'가');const ro=w=>{const j=jong(w);return w+(j&&j!==8?'으로':'로')};
const isHol=d=>d==='none'?false:[0,6].includes(new Date(d+'T12:00:00+09:00').getDay());
const r5=m=>Math.floor(m/5)*5;
const dur=m=>m>=60?`${Math.floor(m/60)}시간${m%60?` ${m%60}분`:''}`:`${m}분`;

/* 플래너 */
const P={day:null,what:'show',show:0,org:null,mode:null,auto:true}; /* auto: 아직 날짜와 할 일을 고르지 않았어요 */
const planDays=()=>{const fut=[...new Set(SHOWS.filter(s=>s.d>TODAY).map(s=>s.d))];return[TODAY,...fut]};
const dayShort=d=>(SHOWS.find(s=>s.d===d)?.day||dayLabel(d)).replace(/요일$/,'');
const renderQ=()=>{const a=document.activeElement,keep=a&&a.tagName==='SELECT'&&a.closest('#pf')?a.id:null;
 if(P.auto){P.day=TODAY;P.what='show'}else if(!P.day||(P.day!=='none'&&P.day<TODAY))P.day=TODAY;
 const dTxt=d=>d==='none'?'다른 날':(d===TODAY?'오늘 · ':'')+dayShort(d);
 $('#qDay').innerHTML=planDays().map(d=>{const n=SHOWS.filter(s=>s.d===d).length;return`<option value="${d}"${P.day===d?' selected':''}>${esc(dTxt(d))} · ${n?`공연 ${n}`:'공연 없음'}</option>`}).join('')+`<option value="none"${P.day==='none'?' selected':''}>다른 날 · 공연 없음</option>`;
 $('#dayTxt').textContent=dTxt(P.day);
 const list=SHOWS.map((s,i)=>({s,i})).filter(o=>o.s.d===P.day);
 if(!list.length)P.what='walk';
 if(P.what==='show'&&!list.some(o=>o.i===P.show))P.show=list[0].i;
 $('#qWhat').innerHTML=list.map(o=>`<option value="s${o.i}"${P.what==='show'&&P.show===o.i?' selected':''}>${esc(o.s.name)} · ${o.s.t}</option>`).join('')+`<option value="walk"${P.what==='walk'?' selected':''}>산책·운동</option>`;
 $('#whatTxt').textContent=P.what==='show'?SHOWS[P.show].name:'산책·운동';
 if(keep){const el=$('#'+keep);el&&el.focus()}};
$('#pf').addEventListener('change',e=>{const t=e.target;P.auto=false;if(t.name==='day')P.day=t.value;else if(t.name==='what'){if(t.value==='walk')P.what='walk';else{P.what='show';P.show=+t.value.slice(1)}}else return;P.mode=null;renderQ();renderPass(true)});
$('#pf').addEventListener('submit',e=>e.preventDefault());
/* 출발역 찾기 */
{const inp=$('#org'),box=$('#orgList'),msg=$('#omsg'),DEF='';let hits=[],cur=-1;
 const nq=q=>q.replace(/\(.*?(\)|$)/g,'').replace(/\s/g,'').replace(/역$/,'');
 const close=()=>{box.hidden=true;inp.setAttribute('aria-expanded','false');inp.removeAttribute('aria-activedescendant');cur=-1};
 const draw=()=>{box.innerHTML=hits.map((i,k)=>`<button type="button" tabindex="-1" role="option" id="og${k}" data-i="${i}" aria-selected="${k===cur}"><span>${esc(TR.name(i))}</span><span class="cap">${esc(TR.linesOf(i).join(', '))}</span></button>`).join('');box.hidden=!hits.length;inp.setAttribute('aria-expanded',String(!!hits.length));if(cur>=0)inp.setAttribute('aria-activedescendant','og'+cur);else inp.removeAttribute('aria-activedescendant')};
 const pick=i=>{P.org=i;P.mode=null;inp.value=TR.name(i)+'역';msg.classList.remove('err');msg.textContent=`출발: ${TR.name(i)}역`;close();renderPass(true)};
 const miss=()=>{msg.classList.add('err');msg.textContent=`'${inp.value.trim()}' 없음`;if(P.org!==null){P.org=null;try{renderPass(false)}catch(e){}}};
 inp.addEventListener('input',()=>{hits=TR.find(inp.value).slice(0,6);cur=-1;draw();msg.classList.remove('err');msg.textContent=DEF;if(!inp.value.trim()&&P.org!==null){P.org=null;renderPass(true)}});
 inp.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();if(cur>=0)return pick(hits[cur]);const h=TR.find(inp.value);if(h.length)pick(h[0]);else if(inp.value.trim())miss();return}
  if(box.hidden)return;if(e.key==='ArrowDown'){cur=Math.min(hits.length-1,cur+1);draw();e.preventDefault()}else if(e.key==='ArrowUp'){cur=Math.max(0,cur-1);draw();e.preventDefault()}else if(e.key==='Escape')close()});
 box.addEventListener('mousedown',e=>e.preventDefault());
 box.addEventListener('click',e=>{const b=e.target.closest('[data-i]');if(b)pick(+b.dataset.i)});
 inp.addEventListener('blur',()=>{close();const q=inp.value.trim();if(!q||(P.org!==null&&inp.value===TR.name(P.org)+'역'))return;const h=TR.find(q),ex=h.find(i=>TR.name(i).replace(/\s/g,'')===nq(q));if(ex!==undefined)pick(ex);else if(!h.length)miss()})}

/* 교통수단 비교 */
const compare=(dest,hour,hol,show)=>{const o=P.org,t=TR.transit(o,dest),c=TR.car(o,dest,hour,hol),b=TR.bike(o,dest),w=TR.walk(o,dest);
 const badWx=P.day===TODAY&&STATE==='live'&&(N.ptype!=='없음'||N.temp<0);
 const back=show?{pt:t?t.min+15:999,car:EXITP50+c.min-8,bike:b.min,walk:w.min}:null;
 const late=show&&t?show.end+15+t.min>=1440:false; /* 공연 끝나고 역까지 15분, 자정 넘어 도착하면 막차가 끊겼을 수 있어요 */
 const M=[
  {k:'pt',min:t?t.min:999,ok:!!t,txt:t?(t.legs.length?t.legs.map(l=>l.line+(l.exp?' 급행':'')).join(' → ')+` → ${TR.name(t.to)}역 + 걷기 ${t.walk}분`:`${TR.name(t.to)}역 + 걷기 ${t.walk}분`)+(t.legs.length>1?` · 환승 ${t.legs.slice(1).map(l=>l.from).join(', ')}`:'')+(late?' · 귀가 자정 넘음':''):'경로 없음'},
  {k:'car',min:c.min,ok:true,txt:`${c.km}km ÷ ${c.v}km/h + 8분(주차·걷기)`+(c.night?' · 18시 속도 적용':'')},
  {k:'bike',min:b.min,ok:b.min<=50&&!badWx,txt:b.min>50?`${b.km}km · 50분 초과`:badWx?'비·눈·영하 · 비추천':`${b.km}km ÷ 13km/h + 6분(대여·반납)`},
  {k:'walk',min:w.min,ok:w.min<=40,txt:w.min>40?`${w.km}km · 40분 초과`:`${w.km}km`}];
 const score=m=>m.min+(back?back[m.k]:0);
 const rec=M.filter(m=>m.ok).sort((a,b)=>score(a)-score(b))[0]||M[0];
 return{M,rec,t,c,b,w,back,late}};
const modeRows=(M,sel)=>`<div class="pmodes" role="group" aria-label="교통수단">${M.map(m=>{const mm=m.min>=999?'없음':dur(m.min);return`<button type="button" class="pmd${m.ok?'':' x'}" data-m="${m.k}" aria-pressed="${m.k===sel}" aria-label="${MODE[m.k][0]}, ${mm}, ${esc(m.txt)}"><span class="pmn">${ic(MODE[m.k][1])}<span>${MODE[m.k][0]}</span></span><span class="pmt">${mm}</span></button>`}).join('')}</div>`;
$('#pass').addEventListener('click',e=>{const b=e.target.closest('.pmd');if(!b)return;P.mode=b.dataset.m;renderPass(true)});

/* 시간표: [시각, 할 일, 덧붙일 말, 종류]. 종류 'wk'는 걷는 구간(발자국 아이콘 + 점선), 덧붙일 말은 산책·운동에서만 보여요 */
const ptl=(rows,caps)=>`<ol class="ptl">${rows.map((r,i)=>r[3]==='wk'?`<li class="sg wk">${ic('footprints')}<span>${esc(r[1])}</span></li>`:`<li class="${i===rows.length-1?'end':r[3]==='soft'?'soft':''}"><span class="t">${hmN(r[0])}</span><span class="l">${esc(r[1])}${r[4]?`<span class="lps">${r[4]}</span>`:''}${caps&&r[2]?`<span class="cap">${esc(r[2])}</span>`:''}</span></li>`).join('')}</ol>`;
/* 방문 계획의 작은 지도: 위 지도 바탕에서 주차장 칸을 빼고, 고른 공연장만 검게 */
const PMAP=(()=>{const w=$('#world');if(!w)return null;const at=(e,k)=>e.getAttribute(k),kids=[...w.children];
 const base=kids.filter(e=>!(e.tagName==='path'&&at(e,'fill')==='#F4F4F5'&&at(e,'stroke')==='#D4D4D8')).map(e=>{const c=e.cloneNode(false);c.removeAttribute('id');return c.outerHTML}).join('');
 const vp=kids.find(e=>at(e,'fill')==='#E4E4E7'&&at(e,'stroke')==='#52525B');
 const subs=(vp?at(vp,'d').match(/M[^M]*/g)||[]:[]).map(d=>{let x=0,y=0,sx=0,sy=0,n=0;for(const[,c,as]of d.matchAll(/([MLl])([^MLlzZ]*)/g)){const a=(as.match(/-?\d*\.?\d+/g)||[]).map(Number);for(let i=0;i+1<a.length;i+=2){if(c==='l'||(c==='M'&&i>0)){x+=a[i];y+=a[i+1]}else{x=a[i];y=a[i+1]}sx+=x;sy+=y;n++}}return{d:d.trim(),x:sx/n,y:sy/n}});
 return{base,subs,vb:[380,150,600,660]}})();
/* 작은 지도: 고른 공연장을 검게, 지하철로 오면 내리는 역에서 공연장까지 걷는 길(직선 점선)과 시간을 지도 안에.
   칸 크기에 맞춰 공연장과 역이 다 들어오게 보는 범위를 다시 잡아요 */
let PMS={};
const drawPmap=()=>{const host=$('#pmap');if(!PMAP||!host)return;const S=PMS,W=host.clientWidth||300,H=host.clientHeight||320,ar=W/H;
 const v=S.venue&&VEN[S.venue],st=S.st;
 const hb=v&&PMAP.subs.map(o=>[Math.hypot(o.x-v[0],o.y-v[1]),o]).sort((a,b)=>a[0]-b[0])[0],hit=hb&&hb[0]<40?hb[1].d:'';
 /* 보는 범위: 공연장·역 둘레 + 이름표 자리(위 70px, 아래 64px, 옆 24px)를 화면 비율에 맞춰 넓힘 */
 let x0,y0,x1,y1;if(v||st){const P_=[v&&[v[0],v[1],v[2]],st&&[st.x,st.y,10]].filter(Boolean);x0=Math.min(...P_.map(q=>q[0]-q[2]));x1=Math.max(...P_.map(q=>q[0]+q[2]));y0=Math.min(...P_.map(q=>q[1]-q[2]));y1=Math.max(...P_.map(q=>q[1]+q[2]))}else{x0=380;y0=150;x1=980;y1=810}
 const on=!!(v||st),fit=(a,b,c,d,u)=>{let w=c-a+(on?u*190:0),h=d-b+(on?u*150:0),cx=(a+c)/2,cy=(b+d)/2-(on?u*4:0);w=Math.max(w,460);h=Math.max(h,360);if(w/h<ar)w=h*ar;else h=w/ar;return[cx-w/2,cy-h/2,w,h]};
 let vb=fit(x0,y0,x1,y1,0);for(let k=0;k<3;k++)vb=fit(x0,y0,x1,y1,vb[2]/W);
 const[vx,vy,vw,vh]=vb,pc=(x,y)=>`left:${((x-vx)/vw*100).toFixed(2)}%;top:${((y-vy)/vh*100).toFixed(2)}%`;
 let walk='';if(v&&st){const dx=v[0]-st.x,dy=v[1]-st.y,L=Math.hypot(dx,dy)||1,ux=dx/L,uy=dy/L,a=[st.x+ux*8,st.y+uy*8],b=[v[0]-ux*(v[2]+6),v[1]-uy*(v[2]+6)];
  walk=`<path class="pmr" d="M${a[0].toFixed(1)} ${a[1].toFixed(1)}L${b[0].toFixed(1)} ${b[1].toFixed(1)}"/>`;S.mid=[(a[0]+b[0])/2,(a[1]+b[1])/2]}
 const flip=!!(v&&st&&st.y<v[1]),near=!!(v&&st&&Math.hypot(v[0]-st.x,v[1]-st.y)/vw*W<130);
 host.innerHTML=`<div class="pmw" role="img" aria-label="${v?esc(S.venue)+' 위치':'올림픽공원 지도'}${st&&v?`, ${esc(st.name)}에서 걸어서 약 ${S.walk}분`:''} (지도 자료: OpenStreetMap)"><svg viewBox="${vb.map(n=>n.toFixed(1)).join(' ')}" preserveAspectRatio="xMidYMid meet" aria-hidden="true"><g class="pmb">${PMAP.base}</g>${hit?`<path class="pmh" d="${hit}"/><path class="pmf" d="${hit}"/>`:''}${walk}</svg>`
  +(st&&v?`${near?'':`<span class="pwk" style="${pc(S.mid[0],S.mid[1])}">${ic('footprints')}도보 약 ${S.walk}분</span>`}<span class="pst" style="${pc(st.x,st.y)}"></span><div class="pstl${flip?' up':''}" style="${pc(st.x,st.y)}"><b>${esc(st.name)}</b><span>${st.lines.map(lnPill).join('')}${st.exit?`<em>${esc(st.exit)}</em>`:''}</span>${near?`<i class="wkt">공연장까지 도보 약 ${S.walk}분</i>`:''}</div>`:'')
  +(v?`<div class="pml${flip?' dn':''}" style="${pc(v[0],flip?v[1]+v[2]:v[1]-v[2])}"><b>${esc(S.venue)}</b><span>${esc(S.sub||'')}</span></div>`:'')+`<span class="pmo">© OpenStreetMap</span></div>`};
const stnOf=(name,venue)=>{const o=STN.find(x=>x[0]===name+'역');return o?{name:o[0],lines:o[1],x:o[3],y:o[4],exit:o[0]==='올림픽공원역'&&venue==='KSPO DOME'?'3번 출구':''}:null};
{let raf=0;const ro=window.ResizeObserver&&new ResizeObserver(()=>{cancelAnimationFrame(raf);raf=requestAnimationFrame(drawPmap)});const h=$('#pmap');if(ro&&h)ro.observe(h)}
/* 공연 포스터: KOPIS 공연 목록에서 같은 날·같은 공연장 공연을 찾아 받아 와요. 못 찾으면 공연장 이름만 보여요 */
const POSTER={};const VKW={'KSPO DOME':['KSPO','체조'],'올림픽홀':['올림픽홀'],'핸드볼경기장':['핸드볼']};
const posterOf=async s=>{const key=`${s.d}|${s.venue}|${s.t}`;if(key in POSTER)return POSTER[key];POSTER[key]='';
 try{const d8=s.d.replace(/-/g,''),j=await getJSON(`/api/kopis?t=list&from=${d8}&to=${d8}&q=${encodeURIComponent('올림픽공원')}`,6000);
  const nz=x=>String(x||'').toLowerCase().replace(/[^0-9a-z가-힣]/g,''),at=(j.rows||[]).filter(r=>r.poster&&(VKW[s.venue]||[]).some(k=>String(r.fcltynm||'').includes(k)));
  const hit=at.find(r=>{const a=nz(r.prfnm);return a&&(a.includes(nz(s.short))||nz(s.name).includes(a))})||(at.length===1?at[0]:null);
  if(hit&&/^https?:\/\/(www\.)?kopis\.or\.kr\//.test(hit.poster))POSTER[key]=hit.poster.replace(/^http:/,'https:')}catch(e){}
 return POSTER[key]};
/* 오늘이면 t분 무렵 올림픽공원 혼잡 단계(서울시 실측·예보에서 가장 가까운 값), 아니면 null */
const crowdAt=t=>{if(P.day!==TODAY||STATE!=='live'||!N||!N.lvl||t<NOWM-10)return null;const pts=[[NOWM,N.lvl,'실측'],...(CITY.fcst||[]).map(f=>[f[0],f[3],'예보'])];if(t>pts[pts.length-1][0]+30)return null;let b=pts[0];for(const q of pts)if(Math.abs(q[0]-t)<Math.abs(b[0]-t))b=q;return b};
const showHead=s=>{const m=s.short&&s.short!==s.name&&s.name.startsWith(s.short)?/^[〈《\[「『<]\s*(.+?)\s*[〉》\]」』>]$/.exec(s.name.slice(s.short.length).trim()):null;return m?[m[1],s.short]:[s.name,s.short&&s.short!==s.name?s.short:'']};

const renderPass=say=>{let cap,title,sub,bigT,bigS,bigH='',msg='',msg2='',why='',rows=[],tips=[],destName='올림픽공원',dest=DEST.park,cmpHtml='',modeTxt='',src='',route='',sh=null,pst=null,pwk=0;
 const org=P.org!==null?TR.name(P.org)+'역':null,hol=isHol(P.day);
 if(P.what==='show'){const s=SHOWS[P.show],p=pred(s);sh=s;destName=s.venue;dest=DEST[s.venue]||DEST.park;title=s.name;sub=`${s.day} · ${s.venue} · ${s.t}`;cap='예상 · 2025 공연 날 기록 · 서울시 교통';
  if(org){const C=compare(dest,(p.st-120)/60,hol,p),m=C.M.find(x=>x.k===(P.mode||C.rec.k)),k=m.k;
   const arr=k==='car'?p.st-120:p.st-45,dep=r5(arr-m.min);bigT=hm(dep);bigS=`${org}에서 ${destName}까지`;bigH=`<span>${esc(org)}</span>${ic('arrow-right')}<span>${esc(destName)}</span>`;modeTxt=`${MODE[k][0]} ${dur(m.min)}`;src=cap;cap='';
   route=k==='pt'?'':esc(m.txt);
   cmpHtml=modeRows(C.M,k);
   if(k==='car'){msg=`${hm(dep)}에 나서면 주차장이 가장 붐비는 ${hm(p.inPk)}보다 30분 먼저 도착해요`;msg2='2025 공연 날 주차 기록 기준';rows=[[dep,`${org} 출발`,'',''],[p.st-120,'주차장 도착','','']]}
   else{msg=`${hm(dep)}에 나서면 공연 45분 전, ${hm(p.st-45)}에 ${destName}에 도착해요`;const cw=crowdAt(p.st-45);if(cw)msg2=`도착 무렵 올림픽공원: ${cw[1]} (서울시 ${cw[2]})`;
    if(k==='pt'){const t=C.t,L=t.legs,pl=l=>lineP(l.line)+(l.exp?'<span class="xp">급행</span>':'');pst=stnOf(TR.name(t.to),s.venue);pwk=t.walk;
     rows=[[dep,`${org} 출발`,'','',L[0]?pl(L[0]):''],...L.slice(1).map((l,n)=>[dep+L[n].t1,`${l.from}역 환승`,'','soft',pl(l)]),[dep+t.min-t.walk,`${TR.name(t.to)}역 도착`,'','soft'],[null,`도보 약 ${t.walk}분`,'','wk'],[p.st-45,`${destName} 도착`,'','']];
     tips.push(C.late?'집에 닿는 때가 자정을 넘어요 · 막차 확인':'돌아갈 때 다른 역: 한성백제역(9) · 몽촌토성역(8)')}
    else rows=[[dep,`${org} 출발`,'',''],[p.st-45,`${destName} 도착`,'','']]}
   if(k==='car')tips=['20시 이후 출차: 북2 + 동2문 71% · 남2문 16% (2025 큰 공연 76일)','내려 주기 10분 이내 = 무료 (입차의 25%)']}
  else{const wk=s.venue==='KSPO DOME'?8:Math.max(5,(TR.transit(OPS,dest)||{walk:8}).walk);pst=stnOf('올림픽공원',s.venue);pwk=wk;bigT=hm(p.st-45);bigS=`${s.venue} 도착`;why='';src=cap;cap='';
   bigH=`${esc(s.venue)} 도착`;msg='출발역을 넣으면 언제 나서야 하는지 알려 드려요';
   rows=[[p.st-45-wk,'올림픽공원역 도착','','soft',lnPill(5)+lnPill(9)+(s.venue==='KSPO DOME'?'<span class="xp">3번 출구</span>':'')],[null,`도보 약 ${wk}분`,'','wk'],[p.st-45,`${s.venue} 도착`,'','']]}
  if(SHOWS.filter(o=>o.d===s.d&&o.t===s.t).length>1)tips.push('같은 시각 공연 2곳 이상');
  tips=tips.map(esc)}
 else{const shows=SHOWS.filter(s=>s.d===P.day);title='산책·운동';let target=null,hour=14;
  const useF=P.day===TODAY&&STATE==='live'&&CITY.fcst.length>0;
  if(useF){cap='서울시 예보';sub='오늘 · '+dayLabel(TODAY);const day_=m=>(m%1440)>=360&&(m%1440)<1320,NC=nowC();const calm=CITY.fcst.filter(f=>f[3]==='여유'&&f[0]>NC&&day_(f[0]));
   if(N.lvl==='여유'&&day_(NC)){target='now';hour=NC/60}else if(calm.length){target=calm[0][0];hour=target/60}
   const R=[];for(const f of CITY.fcst.filter(f=>f[0]>NC&&f[0]<=NC+540)){const l=R[R.length-1];if(l&&l.lvl===f[3]){l.to=f[0];l.lo=Math.min(l.lo,f[1]);l.hi=Math.max(l.hi,f[2])}else R.push({at:f[0],to:f[0],lvl:f[3],lo:f[1],hi:f[2]})}
   rows=R.map(r=>[r.at,`${r.lvl} · ${num(r.lo)}~${num(r.hi)}명`,r.to>r.at?`~ ${hmT(r.to)}`:'',r.lvl==='여유'?'':'soft'])}
  else if(shows.length){cap='예상 · 2025 공연 날 기록';sub=shows[0].day;const e=Math.min(...shows.map(s=>pred(s).inA)),l=Math.max(...shows.map(s=>pred(s).outB));target=e-180;hour=target/60;
   rows=[[e-180,'산책 추천','= 관객 입차 − 3시간',''],[e,'관객 입차 증가',shows.map(s=>`${s.t} ${s.short}`).join(', '),'soft'],[l,'한산','= 출차 몰림 끝','']]}
  else{cap='2025 평일 주차 기록';sub=P.day===TODAY?'오늘 · 공연 없음':'공연 없음';rows=[[480,'입차 최대','평일 08시','soft'],[1080,'출차 증가','평일 18시','']]}
  const later=useF?'부터 한산':'전후 한산';
  if(org){const C=compare(dest,hour,hol,false),m=C.M.find(x=>x.k===(P.mode||C.rec.k));cmpHtml=modeRows(C.M,m.k);route=esc(m.txt);modeTxt=`${MODE[m.k][0]} ${dur(m.min)}`;why=`최단 ${MODE[C.rec.k][0]}`+(C.rec.k==='car'&&P.day===TODAY&&PARK&&PARK.sum/PCAP0>=.9?` · 주차장 ${Math.round(PARK.sum/PCAP0*100)}%`:'');
   if(target==='now'){const d=Math.ceil(nowC()/5)*5;bigT=hm(d);bigS=`${org} 출발 · 한산`;rows.unshift([d,`${org} 출발`,`${MODE[m.k][0]} ${dur(m.min)}`,''])}
   else if(target!==null){const dep=r5(target-m.min);bigT=hm(dep);bigS=`${org} 출발`;rows.unshift([dep,`${org} 출발`,`${MODE[m.k][0]} ${dur(m.min)} → ${hm(target)}${later}`,''])}
   else{bigT='언제든';bigS='공연 없음'}}
  else{why='';
   if(target==='now'){bigT=hm(Math.ceil(nowC()/5)*5);bigS='지금 한산'}else if(target!==null){bigT=hm(target);bigS=later}else{bigT='언제든';bigS='공연 없음'}}
  tips=tips.map(esc)}
 tips.push(esc(org?'자동차 시간 = 거리 ÷ 서울시 시간대별 평균 속도 + 8분':'주차장: 북2 · 동2 · 남2 · 서2문 · 역: 올림픽공원(5·9) · 한성백제(9) · 몽촌토성(8)'));
 if(P.day===TODAY&&STATE==='live'&&N.ptype&&N.ptype!=='없음')tips.push(esc(`오늘 ${N.ptype} · 2025 눈 온 저녁 입차 −62%`));
 const kakao=org?`https://map.kakao.com/link/from/${encodeURIComponent(org)},${TR.ll(P.org).join(',')}/to/${encodeURIComponent(destName)},${dest.join(',')}`:`https://map.kakao.com/link/search/${encodeURIComponent(destName)}`;
 if(src)tips.unshift(esc(src));
 const a=document.activeElement,km=a&&a.closest&&a.closest('#pass .pmd')?a.dataset.m:null;
 $('#pass').innerHTML=`${cap?`<p class="cap">${cap}</p>`:''}<div class="pbig"><b>${bigT}</b><span class="rt">${bigH||esc(bigS)}</span></div>${msg?`<div class="pmsg"><p>${esc(msg)}</p>${msg2?`<p class="cap">${esc(msg2)}</p>`:''}</div>`:''}${cmpHtml}${route?`<p class="prt">${route}</p>`:''}${ptl(rows,!sh)}`;
 $('#ptips').innerHTML=tips.map(t=>`<span>${t}</span>`).join('');
 if(km){const el=$(`#pass .pmd[data-m="${km}"]`);el&&el.focus()}
 /* 왼쪽: 공연 정보 */
 {const p=sh&&pred(sh),[ti,by]=sh?showHead(sh):[title,sub],key=sh?`${sh.d}|${sh.venue}|${sh.t}`:'';
  const dl=sh?[['공연 날짜',sh.day.replace(/\s?(.)요일$/,' ($1)')],['공연 시각',p.assumed?`${sh.t} ~`:`${sh.t} ~ ${hm(p.end)}`],['장소',sh.venue]]:[['날짜',P.day==='none'?'공연 없는 날':dayShort(P.day).replace(/\s(.)$/,' ($1)')],['장소','올림픽공원']];
  $('#pshow').innerHTML=`<h3 id="passH" tabindex="-1">${esc(ti)}</h3>${by?`<p class="pby">${esc(by)}</p>`:''}<div class="ppos" id="ppos" data-k="${esc(key)}"><span>${esc(destName)}</span></div><dl class="pdl">${dl.map(r=>`<div><dt>${r[0]}</dt><dd>${esc(r[1])}</dd></div>`).join('')}</dl>`;
  if(sh)posterOf(sh).then(u=>{const b=$('#ppos');if(!u||!b||b.dataset.k!==key)return;const im=new Image();im.alt=`${sh.name} 포스터`;im.referrerPolicy='no-referrer';im.onload=()=>{if(b.isConnected&&b.dataset.k===key){b.textContent='';b.appendChild(im);b.classList.add('has')}};im.src=u})}
 /* 오른쪽: 공연장 지도와 길찾기 */
 PMS={venue:sh?sh.venue:'',sub:sh?`${sh.t} ${sh.short}`:'',st:pst,walk:pwk};drawPmap();
 $('#pkakao').href=kakao;
 if(say)$('#srPass').textContent=`${title}. ${bigT}${/^(에|까지|부터|전후|이면)/.test(bigS)?'':' '}${bigS}.${modeTxt?' '+modeTxt+'.':''}`};

/* 그래프 */
const mk=(id,label,fn)=>{const s=$(id);s.setAttribute('aria-label',label);const draw=()=>{const W=s.clientWidth,H=s.clientHeight;if(W)s.innerHTML=fn(W,H)};new ResizeObserver(draw).observe(s)};
const base=REF.base.rows,sat=REF.sat.rows;
const eve=r=>r[0]>=960&&r[0]<1200;
const satEve=Math.max(...sat.filter(eve).map(r=>r[1])),baseEve=Math.max(...base.filter(eve).map(r=>r[1]));
$('#i1').textContent=`${(satEve/baseEve).toFixed(1)}배`;
$('#i1t').textContent=`16–20시 최대: 공연 날 ${num(satEve)}대 ÷ 평일 ${num(baseEve)}대`;
const ln=(pts,o={})=>`<path d="${pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+','+p[1].toFixed(1)).join('')}" fill="none" stroke="${o.c||'#0A0A0A'}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"${o.dash?' stroke-dasharray="6 4"':''}/>`;
const yax=(ticks,L,R,W,Y,fmt)=>ticks.map(v=>`<line x1="${L}" x2="${W-R}" y1="${Y(v)}" y2="${Y(v)}" stroke="#E5E5E5"/><text x="${L-8}" y="${Y(v)+4.5}" text-anchor="end">${fmt(v)}</text>`).join('');
const xax=(ticks,X,H,B,fmt)=>ticks.map(t=>`<text x="${X(t)}" y="${H-B+22}" text-anchor="middle">${fmt(t)}</text>`).join('');
const unit=(W,R,t)=>`<text x="${W-R}" y="-10" text-anchor="end">${t}</text>`;
const pk1=sat.filter(r=>r[0]>=360&&r[0]<=1440).reduce((m,r)=>r[1]>m[1]?r:m);
mk('#f1',`공연 날 주차장 안 차량은 ${hm(pk1[0])}에 ${num(pk1[1])}대로 가장 많았어요. 공연 없는 평일은 저녁에 가장 많을 때 ${num(baseEve)}대였어요.`,(W,H)=>{const L=48,R=8,T=8,B=30,x0=360,x1=1440,ym=3600,X=t=>L+(t-x0)/(x1-x0)*(W-L-R),Y=v=>T+(1-v/ym)*(H-T-B);
 const a=sat.filter(r=>r[0]>=x0&&r[0]<=x1),b=base.filter(r=>r[0]>=x0&&r[0]<=x1),pk=pk1;
 return unit(W,R,'단위: 대')+yax([0,1000,2000,3000],L,R,W,Y,v=>v.toLocaleString('ko-KR'))+`<line x1="${L}" x2="${W-R}" y1="${Y(0)}" y2="${Y(0)}" stroke="#D4D4D8"/>`+ln(b.map(r=>[X(r[0]),Y(r[1])]),{c:'#6B6B74',dash:1})+ln(a.map(r=>[X(r[0]),Y(r[1])]))+`<circle cx="${X(pk[0])}" cy="${Y(pk[1])}" r="4" fill="#0A0A0A"/><text class="v" x="${X(pk[0])-10}" y="${Y(pk[1])+4}" text-anchor="end" style="${halo}">${hm(pk[0])} ${num(pk[1])}대</text>`+xax(W<520?[480,960,1440]:[480,720,960,1200,1440],X,H,B,t=>(t%1440)/60+'시')});
mk('#f2','12월 6일 공연 날 10분 동안 들어오고 나간 차량 수. 공연 시작 2시간 전부터 들어오는 차가 많았고, 공연 중에는 10분에 20~30대로 줄었고, 끝나고 80분 뒤 나가는 차가 가장 많았어요.',(W,H)=>{const L=40,R=8,T=8,B=30,x0=840,x1=1440,ym=340,X=t=>L+(t-x0)/(x1-x0)*(W-L-R),Y=v=>T+(1-v/ym)*(H-T-B);
 const a=sat.filter(r=>r[0]>=x0&&r[0]<=x1);
 return unit(W,R,'단위: 대')+`<rect x="${X(1080)}" y="${T}" width="${X(1230)-X(1080)}" height="${Y(0)-T}" fill="#F4F4F5"/>`+yax([0,100,200,300],L,R,W,Y,v=>v)+`<line x1="${L}" x2="${W-R}" y1="${Y(0)}" y2="${Y(0)}" stroke="#D4D4D8"/>`+ln(a.map(r=>[X(r[0]),Y(r[3]+r[4]+r[5]+r[6]+r[7])]),{c:'#A1A1AA'})+ln(a.map(r=>[X(r[0]),Y(r[2])]))+xax(W<520?[900,1140,1380]:[900,1020,1140,1260,1380],X,H,B,t=>hm(t))});
const f3rows=[['남2문',124],['북2문',99],['동2문',93],['서2문',Math.max(...sat.map(r=>r[6]))]];
mk('#f3',`공연 뒤 10분 동안 출구별로 나간 가장 많은 차량 수. ${f3rows.map(([n,v])=>`${n} ${v}대`).join(', ')}.`,(W,H)=>{const L=64,R=56,gap=36,T=6;
 return f3rows.map(([n,v],i)=>{const y=T+i*gap,w=(W-L-R)*v/130;return`<text x="${L-12}" y="${y+10}" text-anchor="end" style="font-size:14px">${n}</text><rect x="${L}" y="${y}" width="${W-L-R}" height="12" rx="2" fill="#F4F4F5"/><rect x="${L}" y="${y}" width="${w}" height="12" rx="2" fill="${i===0?'#0A0A0A':'#A1A1AA'}"/><text class="v" x="${L+w+8}" y="${y+10}" style="font-size:14px">${v}대</text>`}).join('')});
const hb=HOURLY['평일 평균'],hs=HOURLY['12/4 목 저녁 눈'];
mk('#f4',`한 시간 동안 들어온 차량 수. 눈이 온 12월 4일 저녁 7시에는 ${hs[19]}대로, 공연 없는 평일 평균 ${hb[19]}대보다 62% 적었어요.`,(W,H)=>{const L=48,R=8,T=8,B=30,x0=6,x1=23,ym=1600,X=h=>L+(h-x0)/(x1-x0)*(W-L-R),Y=v=>T+(1-v/ym)*(H-T-B);
 const Pp=a=>a.map((v,h)=>[h,v]).filter(p=>p[0]>=x0&&p[0]<=x1).map(p=>[X(p[0]),Y(p[1])]);
 return unit(W,R,'단위: 대')+`<rect x="${X(18.5)}" y="${T}" width="${X(23)-X(18.5)}" height="${Y(0)-T}" fill="#F4F4F5"/>`+yax([0,500,1000,1500],L,R,W,Y,v=>v.toLocaleString('ko-KR'))+`<line x1="${L}" x2="${W-R}" y1="${Y(0)}" y2="${Y(0)}" stroke="#D4D4D8"/>`+ln(Pp(hb),{c:'#6B6B74',dash:1})+ln(Pp(hs))+`<line x1="${X(19)}" x2="${X(19)}" y1="${T+44}" y2="${Y(hs[19])-6}" stroke="#A1A1AA"/><circle cx="${X(19)}" cy="${Y(hs[19])}" r="4" fill="#0A0A0A"/><text x="${W-R}" y="${T+16}" text-anchor="end">눈 온 저녁</text><text class="v" x="${W-R}" y="${T+36}" text-anchor="end" style="${halo}">19시 ${hs[19]}대, 평소 ${hb[19]}대</text>`+xax(W<520?[6,12,18]:[6,9,12,15,18,21],X,H,B,h=>h+'시')});

/* 출구별로 출차 80%가 끝난 시각 (작년 12월 6일) */
{const st=REF.sat.start,end=st+150,G=[['북2문',3],['동2문',4],['남2문',5]].map(([n,g])=>{const post=sat.filter(r=>r[0]>=end),tot=post.reduce((a,r)=>a+r[g],0);let c=0,t80=null;for(const r of post){c+=r[g];if(t80===null&&c>=.8*tot)t80=r[0]}return[n,t80]});
 const by=G.reduce((m,[n,t])=>{(m[t]=m[t]||[]).push(n);return m},{}),ks=Object.keys(by).map(Number).sort((a,b)=>a-b);
 $('#i3t').textContent=ks.map(t=>`${by[t].join('·')} ${hm(t)}`).join(' · ')}

/* 주차장 예측 정확도: 2025년 입출차 1년치, 한 달씩 빼 두고 예측하는 검증 (2026-11-24 계산) */
{const LAD=[['시간대만',79.8,'하루 중 시각',''],['요일',83.7,'월–목 · 금 · 토 · 일','p < 0.01'],['공휴일과 명절',86.0,'공휴일 · 낀 공휴일 · 설·추석','p < 0.01'],['공연 정보',86.7,'공연 유무 · 관객 규모 (한국체육산업개발)','p < 0.01'],['지난주 실측',87.7,'직전 7일 실측','+0.9%p · 유의 아님'],['2시간 전 실제 값',92.3,'2시간 전 실측 (실시간 주차현황) 보정','p < 0.01']];
 $('#lad').innerHTML=LAD.map(([n,v,d,j],i)=>`<li><span class="n">${i?'+ ':''}${n}<span class="cap">${d}${j?`<br>${j}`:''}</span></span><span class="bar"><i style="width:${v}%${i>=4?';background:var(--ink)':''}"></i></span><b>${v.toFixed(1)}%</b></li>`).join('');
 $('#lad').setAttribute('aria-label',LAD.map(([n,v])=>`${n} ${v}%`).join(', '))}

/* 서울시 예보 적중률: 처음엔 들어 있는 값, /api/acc(최근 7일, 매시간 다시 계산)를 받으면 그 값 */
const ACC1=(lv,n,per)=>{$('#acc1').innerHTML=`서울시 예보 적중 ${lv}% (3시간 앞, ${per}) · <a href="/hub#accuracy">정확도</a>`};
const ACCP=getJSON('/api/acc',7000).catch(()=>null);
ACCP.then(j=>{const h=j&&j.ok&&(j.horizon||[]).find(x=>x.h===3);if(h&&h.n>=100)ACC1(h.level,h.n,`최근 ${j.days}일`)});
/* 정확도: analyze_accuracy.py가 만든 숫자 */
if(ACC){const H=ACC.horizon,h3=H.find(x=>x.h===3)||H[0],nF=H.reduce((a,x)=>a+x.n,0),pd=ACC.period;
 const fd=s=>`${+s.slice(5,7)}월 ${+s.slice(8,10)}일 ${+s.slice(11,13)}시`;
 const man=v=>v>=10000?(v/10000).toFixed(v%10000?1:0)+'만':v>=1000?(v/1000)+'천':String(v);
 ACC1(h3.level,h3.n,`${+pd[0].slice(5,7)}/${+pd[0].slice(8,10)}–${+pd[1].slice(5,7)}/${+pd[1].slice(8,10)}`);
 $('#accLead').textContent=`주차장: 입출차 2025 · 혼잡 시간·예보: 서울시 실시간 (5분 간격)`;
 const S=ACC.show;
 if(S&&S.days){const R=S.detail.flatMap(d=>d.rows),n=R.length,both=R.filter(r=>r.ok_seoul&&r.ok_ours).length,fix=R.filter(r=>!r.ok_seoul&&r.ok_ours),worse=R.filter(r=>r.ok_seoul&&!r.ok_ours).length,miss=n-both-fix.length-worse,pc=v=>Math.round(100*v/n);
  $('#a1').textContent=`${S.seoul}% → ${S.ours}%`;
  $('#a1t').innerHTML=`<dl class="kv"><div><dt>대상</dt><dd>${S.detail.map(d=>mdLabel(d.date)).join(', ')} · 14–23시 정시 ${n}개</dd></div><div><dt>서울시 예보 (3시간 전)</dt><dd>${S.seoul}%</dd></div><div><dt>+ 공연 −30분 ~ 종료 +30분</dt><dd>${S.ours}%${fix.length?` (${fix.map(r=>+r.t.slice(0,2)+'시').join(', ')} 보정)`:''}</dd></div><div><dt>공연일 수</dt><dd>${S.days}</dd></div></dl>`;
  const seg=[[both,'#0A0A0A',`예보 적중 ${pc(both)}%`],[fix.length,'#6B6B74',`공연 보정 +${pc(fix.length)}%`],[worse,'#FCA5A5',`보정 오류 ${pc(worse)}%`],[miss,'#E5E5E5',`미적중 ${pc(miss)}%`]].filter(x=>x[0]);
  $('#a1b').innerHTML=seg.map(([v,c])=>`<span style="flex:${v};background:${c}"></span>`).join('');$('#a1b').setAttribute('aria-label',seg.map(x=>x[2]).join(', '));
  $('#a1l').innerHTML=seg.map(([v,c,t])=>`<span><i style="width:12px;height:12px;border:0;background:${c}"></i>${t}</span>`).join('')}
 const C=ACC.case;
 if(C){const sh=C.shows[0],st=toM(sh.t),w0=st-30,w1=st+(sh.run||150)+30,mid=r=>(r[1]+r[2])/2;
  $('#a1c').textContent=`${mdLabel(C.date)} ${sh.name} · 공원 인구 (명) · 예보 발표 ${C.issued} · 실측 = 5분 값 3개 중앙값`;
  const pk=C.fcst.reduce((m,r)=>r[2]>m[2]?r:m,C.fcst[0]),apk=C.actual.reduce((m,r)=>r[2]>m[2]?r:m,C.actual[0]);
  mk('#a1f',`예보 최대 ${hm(pk[0])} ${num(pk[1])}~${num(pk[2])}명 (발표 ${C.issued}) · 실측 최대 ${hm(apk[0])} ${num(apk[1])}~${num(apk[2])}명`,(W,Hh)=>{const L=48,R=8,T=8,B=30,x0=720,x1=1410,ym=20000,X=t=>L+(t-x0)/(x1-x0)*(W-L-R),Y=v=>T+(1-v/ym)*(Hh-T-B);
   const a0=C.actual.filter(r=>r[0]>=x0&&r[0]<=x1),a=a0.map((r,i)=>{const v=[a0[i-1]||r,r,a0[i+1]||r].map(mid).sort((p,q)=>p-q)[1];return[r[0],v,v]}); /* 한 번 튀는 값은 앞뒤 3개의 중앙값으로 걸러요 */
   return unit(W,R,'단위: 명')+`<rect x="${X(w0)}" y="${T}" width="${X(Math.min(w1,x1))-X(w0)}" height="${Y(0)-T}" fill="#EEEEF0"/><text x="${X(w0)+6}" y="${T+16}" style="fill:#0A0A0A">${esc(sh.name)} ${sh.t} 공연</text>`+yax([0,5000,10000,15000,20000],L,R,W,Y,man)+`<line x1="${L}" x2="${W-R}" y1="${Y(0)}" y2="${Y(0)}" stroke="#D4D4D8"/>`+ln(C.fcst.map(r=>[X(r[0]),Y(mid(r))]),{c:'#6B6B74',dash:1})+ln(a.map(r=>[X(r[0]),Y(mid(r))]))+xax(W<520?[780,1020,1260]:[780,900,1020,1140,1260,1380],X,Hh,B,t=>t/60+'시')})}
 const sel=[1,3,6,12],per0=`${+pd[0].slice(5,7)}/${+pd[0].slice(8,10)}–${+pd[1].slice(5,7)}/${+pd[1].slice(8,10)}`;let A2H=H;
 const a2draw=(W,Hh)=>{const H=A2H,L=40,R=8,T=20,B=30,n=H.length,bw=(W-L-R)/n,Y=v=>T+(1-v/100)*(Hh-T-B);
  return yax([0,50,100],L,R,W,Y,v=>v+'%')+H.map((x,i)=>{const xx=L+i*bw+bw*.2,w=bw*.6;return`<rect x="${xx}" y="${Y(x.level)}" width="${w}" height="${Y(0)-Y(x.level)}" rx="2" fill="${x.h===3?'#0A0A0A':'#A1A1AA'}"/>`+(sel.includes(x.h)?`<text class="v" x="${xx+w/2}" y="${Y(x.level)-6}" text-anchor="middle">${x.level}%</text><text x="${xx+w/2}" y="${Hh-B+22}" text-anchor="middle">${x.h}시간</text>`:'')}).join('')};
 const A2=(Hx,per)=>{A2H=Hx;const h3=Hx.find(x=>x.h===3)||Hx[0],nF=Hx.reduce((a,x)=>a+x.n,0);
  $('#a2').textContent=`${Math.min(...Hx.map(x=>x.level))}–${Math.max(...Hx.map(x=>x.level))}%`;
  $('#a2t').innerHTML=`<dl class="kv"><div><dt>비교</dt><dd>예보 ${num(nF)}건 · 1–12시간 앞 · ${per}</dd></div><div><dt>3시간 앞</dt><dd>${h3.level}%</dd></div><div><dt>인원 구간 일치 (${per0})</dt><dd>${Math.min(...H.map(x=>x.band))}–${Math.max(...H.map(x=>x.band))}%</dd></div><div><dt>인원 평균 오차 (${per0})</dt><dd>${num(Math.min(...H.map(x=>x.err)))}–${num(Math.max(...H.map(x=>x.err)))}명</dd></div></dl>`;
  const sv=$('#a2f');sv.setAttribute('aria-label',Hx.map(x=>`${x.h}시간 후 ${x.level}%`).join(', '));if(sv.clientWidth)sv.innerHTML=a2draw(sv.clientWidth,sv.clientHeight)};
 mk('#a2f','',a2draw);A2(H,per0);
 ACCP.then(j=>{if(j&&j.ok&&Array.isArray(j.horizon)&&j.horizon.length>=6)A2(j.horizon,`최근 ${j.days}일`)});
 const M=ACC.share;
 if(M&&M.subway_pct!==null){const tot=M.subway+M.bus;
  $('#a3').textContent=`대중교통 중 지하철 ${M.subway_pct}%`;
  $('#a3t').innerHTML=`<dl class="kv"><div><dt>대상</dt><dd>금요일 KSPO DOME 공연일 ${M.days.map(d=>mdLabel(d)).join(', ')}</dd></div><div><dt>하차 증가</dt><dd>+${num(tot)}명 = 지하철 ${num(M.subway)} + 버스 ${num(M.bus)}</dd></div><div><dt>제외</dt><dd>자동차 · 택시 · 도보</dd></div></dl><p class="cap">출처: 서울시 교통카드 승하차</p>`;
  mk('#a3f',`지하철 ${num(M.subway)}명, ${M.subway_pct}%. 버스 ${num(M.bus)}명, ${100-M.subway_pct}%.`,(W,Hh)=>{const L=0,R=0,w=W-L-R,a=w*M.subway/tot;
   return`<rect x="${L}" y="20" width="${a-1}" height="28" rx="2" fill="#0A0A0A"/><rect x="${L+a+1}" y="20" width="${w-a-1}" height="28" rx="2" fill="#A1A1AA"/><text class="v" x="${L}" y="72">지하철 ${M.subway_pct}%</text><text x="${L}" y="92">${num(M.subway)}명</text><text class="v" x="${W}" y="72" text-anchor="end">버스 ${100-M.subway_pct}%</text><text x="${W}" y="92" text-anchor="end">${num(M.bus)}명</text>`})}}

/* 정확도만 보여 줄 때는 여기까지: 실시간 데이터, 열차, 분실물은 부르지 않아요 */
if(ONLY)return;
/* 분실물 */
const icon=n=>/지갑/.test(n)?'wallet':/키/.test(n)?'key-round':/여행용/.test(n)?'luggage':/가방|쇼핑백|파우치/.test(n)?'shopping-bag':/이어폰/.test(n)?'headphones':/워치/.test(n)?'watch':/휴대폰/.test(n)?'smartphone':/카메라/.test(n)?'camera':/선글라스/.test(n)?'glasses':/모자|외투/.test(n)?'shirt':/수첩/.test(n)?'notebook-pen':/킥보드/.test(n)?'bike':'toy-brick';
let lf='전체',showAll=false;
const stc=s=>s==='보관 중'?'s-keep':s==='경찰서 이관'?'s-pol':'s-back';
$('#lf').innerHTML=['전체','보관 중','경찰서 이관','반환 완료'].map(f=>`<button type="button" data-f="${f}" aria-pressed="${f===lf}">${f}</button>`).join('');
const STOP=/^(근처|부근|주변|잃어버렸어요|잃어버렸어|잃어버림|찾아요|찾고|있어요)$/;
const renderLost=()=>{const q=$('#lq').value.trim(),syn=[];
 const words=q.split(/\s+/).map(w=>{const b=w.replace(/(을|를|에서|에|은|는|이|가|도)$/,''),m=SYN[w]||SYN[b];if(m&&m!==b)syn.push([b,m]);return m||b}).filter(w=>w.length>0&&!STOP.test(w));
 const dm=q.match(/(\d{1,2})\s*월\s*(\d{1,2})\s*일/),dkey=dm?`-${String(dm[1]).padStart(2,'0')}-${String(dm[2]).padStart(2,'0')}`:null;
 let rows=LOST.filter(r=>lf==='전체'||r.st===lf);
 if(dkey){rows=rows.filter(r=>r.d.endsWith(dkey))}else if(words.length){const sc=r=>words.filter(w=>(r.item+r.place).replace(/\s/g,'').includes(w)).length+(words.includes(r.item.replace(/\s/g,''))?.5:0);rows=rows.filter(r=>sc(r)>0).sort((a,b)=>sc(b)-sc(a))}
 const total=rows.length,cut=!words.length&&!showAll&&rows.length>12;if(cut)rows=rows.slice(0,12);
 $('#items').innerHTML=rows.map(r=>`<div class="lr" tabindex="-1">${ic(icon(r.item))}<div><h3>${esc(r.item)}</h3><p class="pl">${esc(r.place)}</p></div><span class="d num">${+r.d.slice(5,7)}월 ${+r.d.slice(8)}일</span><span class="c">${r.center}</span>${r.st==='경찰서 이관'?`<a class="s ${stc(r.st)}" href="https://www.lost112.go.kr" target="_blank" rel="noopener" aria-label="경찰서 이관, lost112에서 찾기, 새 창">${r.st}</a>`:`<span class="s ${stc(r.st)}">${r.st}</span>`}</div>`).join('')||`<p class="lbl" style="padding:16px 0">0건 · 1개월 경과 → lost112.go.kr</p>`;
 $('#lmore').innerHTML=cut?`<button class="btn sec" type="button" id="lmb">${total-12}건 더 보기</button>`:'';
 $('#lm').textContent=words.length?`${total}건`+syn.map(([a,b])=>` · ${a} = ${b}`).join(''):(()=>{const ds=LOST.map(r=>r.d).sort(),f=d=>`${+d.slice(5,7)}/${+d.slice(8)}`;return`공고 ${LOST.length}건 · ${f(ds[0])}–${f(ds[ds.length-1])} · 보관 중 ${LOST.filter(r=>r.st==='보관 중').length}`})()};
$('#lf').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;lf=b.dataset.f;$$('#lf button').forEach(x=>x.setAttribute('aria-pressed',x===b));renderLost()});
$('#lq').addEventListener('input',renderLost);
$('#lmore').addEventListener('click',e=>{if(e.target.closest('#lmb')){showAll=true;renderLost();const r=$$('#items .lr')[12];r&&r.focus()}});

/* 지도 영역 탭: 주차·출입문 / 걷는 길 혼잡 / 오늘 추이. 끼워 넣은 화면은 처음 열 때 불러오고 높이를 내용에 맞춰요 */
{const fit=f=>{try{const d=f.contentDocument;if(d&&d.body)f.style.height=Math.ceil(Math.max(d.body.offsetHeight,d.documentElement.scrollHeight)+2)+'px'}catch(e){}};
 const tabs=$$('.ptabs [role=tab]');
 const pick=id=>{tabs.forEach(t=>{const on=t.id===id,pv=document.getElementById(t.getAttribute('aria-controls'));t.setAttribute('aria-selected',on);t.tabIndex=on?0:-1;pv.hidden=!on;
   if(on){const f=pv.querySelector('iframe[data-src]');if(f&&!f.src){f.addEventListener('load',()=>{fit(f);try{new ResizeObserver(()=>fit(f)).observe(f.contentDocument.body)}catch(e){}});f.src=f.dataset.src}else if(f)fit(f)}})};
 $('.ptabs').addEventListener('click',e=>{const t=e.target.closest('[role=tab]');if(t)pick(t.id)});
 $('.ptabs').addEventListener('keydown',e=>{if(e.key!=='ArrowRight'&&e.key!=='ArrowLeft')return;const i=tabs.indexOf(document.activeElement);if(i<0)return;const n=tabs[(i+(e.key==='ArrowRight'?1:tabs.length-1))%tabs.length];pick(n.id);n.focus();e.preventDefault()});
 pick('pt-map');
 /* 방문 계획에서 고른 날과 시각을 위 지도로 */
 $('#toMap').onclick=()=>{const d=!P.day||P.day==='none'?TODAY:P.day,sh=P.what==='show'?SHOWS[P.show]:null,t=sh?pred(sh).inPk:d===TODAY?nowC():900;
  if(timer)stop();pick('pt-map');setView(d);userT=true;renderView(true);setT(t);sayT();$('#now').scrollIntoView({behavior:smooth()});$('#tr').focus({preventScroll:true})}}

/* 탭 위치 */
{const secs=['now','plan','lost'].map(id=>document.getElementById(id));const tabs=$$('.tabs a');
 const spy=()=>{const y=window.scrollY+window.innerHeight*.3;let cur=secs[0];for(const s of secs)if(s.offsetTop<=y)cur=s;tabs.forEach(a=>a.setAttribute('aria-current',a.getAttribute('href')==='#'+cur.id))};
 addEventListener('scroll',spy,{passive:true});spy()}

/* 처음 그리기: 서울시 데이터 없이 먼저 그리고, 들어오면 다시 그려요 */
CITY=blankCity();derive();renderHero();renderView(true);renderQ();renderPass(false);renderLost();
const load=async()=>{STATE='pending';renderHero();
 const[cr,pr]=await Promise.allSettled([getJSON('/api/now',7000),getJSON('/api/parking',7000)]);
 const ok=cr.status==='fulfilled'&&cr.value&&cr.value.now&&cr.value.now.time&&cr.value.now.lo!=null;
 PARK=pr.status==='fulfilled'&&pr.value&&pr.value.ok?pr.value:null;STATE=ok?'live':'fail';CITY=ok?cr.value:blankCity();derive();
 const hadF=document.activeElement===$('#retry');
 renderHero();renderView(false);renderQ();renderPass(false);
 if(hadF)(STATE==='fail'?$('#retry'):$('#heroH')).focus()};
/* 올림픽공원역 다음 열차: 서울시가 정보를 만든 시각(recptnDt)에서 지난 시간만큼 당겨서 보여줘요 */
let TRAIN=null;
const LINE=id=>{const n=+id-1000;return n>=1&&n<=9?`${n}호선`:''};
const kstMs=s=>Date.parse(String(s).replace(' ','T')+'+09:00');
const etaOf=(t,now)=>{if(t.cd==='2')return null;
 const el=Math.max(0,(now-kstMs(t.at))/1000)||0,mins=s=>s<-30?null:s<=40?{s:0,x:'곧 도착'}:{s,x:`${Math.ceil(s/60)}분`};
 if(t.cd==='0'||t.cd==='1')return el<90?{s:0,x:'곧 도착'}:null;
 if(t.sec>0)return mins(t.sec-el);
 let m=t.msg.match(/\[(\d+)\]번째 전역/);if(m)return el<60?{s:+m[1]*120,x:`${m[1]}정거장 전`}:mins(+m[1]*120-el);
 if(/전역 (도착|출발|진입)/.test(t.msg))return el<60?{s:90,x:'1정거장 전'}:mins(90-el);
 m=t.msg.match(/(\d+)분\s*(?:(\d+)초)?\s*후/);if(m)return mins(+m[1]*60+(+m[2]||0)-el);
 return null};
const renderTrain=()=>{const box=$('#train');
 if(!TRAIN||!TRAIN.ok||Date.now()-Date.parse(TRAIN.fetchedAt)>600000){box.hidden=true;return}
 const now=Date.now(),G=new Map();
 for(const t of TRAIN.list){const ln=LINE(t.id),e=ln&&etaOf(t,now);if(!e)continue;
  const way=((t.line.split(' - ')[1]||'').replace(/\s*\(.*$/,'').replace(/방면$/,' 방면').trim())||t.updn,k=t.id+'|'+t.updn;
  if(!G.has(k))G.set(k,{ln,id:t.id,way,ts:[]});G.get(k).ts.push({...e,d:`${t.dest}행${t.exp?' 급행':''}${t.last?' 막차':''}`})}
 const rows=[...G.values()].sort((a,b)=>a.id.localeCompare(b.id)||a.way.localeCompare(b.way)).map(g=>{const ts=g.ts.sort((a,b)=>a.s-b.s).slice(0,2);
  return`<li><span class="t">${lnPill(+g.id-1000)}</span><span>${esc(g.way)}<span class="cap">${[...new Set(ts.map(x=>x.d))].map(esc).join(', ')}</span></span><span class="eta">${ts.map((x,i)=>i?`<span>${x.x}</span>`:`<b>${x.x}</b>`).join('')}</span></li>`}).join('');
 const at=TRAIN.list.map(t=>t.at).sort().pop()||'';
 if(!rows){box.hidden=true;return}
 box.hidden=false;box.innerHTML=`<h2 class="h-sub">올림픽공원역 다음 열차</h2><ul class="shl trl">${rows}</ul><p class="cap">출처: 서울시${at?` · ${esc(at.slice(11,16))}`:''}</p>`};
const loadTrain=async()=>{try{TRAIN=await getJSON('/api/subway',7000)}catch(e){}renderTrain()};
loadTrain();
setInterval(()=>{if(document.visibilityState==='visible')loadTrain();else renderTrain()},30000);
$('#retry').onclick=()=>{$('#retry').dataset.busy='1';load()};
/* 열어 둔 채로 있어도 최신으로: 1분마다 '지금' 표시, 5분마다 서울시 데이터를 조용히 다시 받아요 */
setInterval(()=>{if(VIEW===TODAY)drawNow();renderTrain()},60000);
setInterval(async()=>{if(document.visibilityState!=='visible'||STATE==='pending')return;try{const c=await getJSON('/api/now',7000);if(!c||!c.now||c.now.lo==null||(STATE==='live'&&c.now.time===N.time))return;const p=await getJSON('/api/parking',7000).catch(()=>null);if(p&&p.ok)PARK=p;STATE='live';CITY=c;derive();renderHero();renderView(false);renderPass(false)}catch(e){}},300000);
addEventListener('message',e=>{if(e.origin===location.origin&&e.data&&e.data.olltimeH>200){const f=document.getElementById('secf');if(f)f.style.height=e.data.olltimeH+'px'}});
getJSON('/api/trend',7000).then(j=>{PT=(j&&j.ok?j.list:[]).filter(r=>r[1]!=null).map(r=>[r[0],r[1]]);
 /* 지난 시간 인원: 서울시가 측정한 시각 기준 (예전 기록은 저장 시각 − 30분) */
 {const seen=new Set();PP=(j&&j.ok?j.list:[]).filter(r=>r[2]!=null&&r[4]).map(r=>[r[5]!=null?r[5]:r[0]-30,r[2],r[3],NLV(r[4])]).filter(r=>!seen.has(r[0])&&seen.add(r[0])).sort((a,b)=>a[0]-b[0])}if(STATE==='live'&&PT.length)renderView(false);const v=(j&&j.ok?j.list:[]).filter(r=>r[1]!=null&&r[0]>=120&&r[0]<=300).map(r=>r[1]).sort((a,b)=>a-b);if(v.length>=6){FLOORP=v[Math.floor(v.length/2)];FLOORD=true;if(STATE==='live')renderHero()}}).catch(()=>{});
$('#heroH').setAttribute('tabindex','-1');
await load();
})();
</script>
</body>
</html>
