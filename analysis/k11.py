import pandas as pd,numpy as np,re,json,warnings;warnings.filterwarnings('ignore')
df=pd.read_csv('inout_2025_full.csv',usecols=['entry_gate','entry_time','exit_time'],encoding='utf-8-sig');e=pd.to_datetime(df.entry_time);x=pd.to_datetime(df.exit_time);st=(x-e).dt.total_seconds()/60
g=df.entry_gate.astype(str).str.split('입구').str[0];ok=(st>=10)&(st<4320)
L=pd.read_csv('linked_2025.csv',encoding='utf-8-sig',usecols=['datetime','perf_name','perf_audience']);L=L[L.perf_name.notna()&(L.perf_name!='')];L['d']=L.datetime.str[:10];L['hh']=L.datetime.str[11:13].astype(int)
S=L.groupby('d').agg(h0=('hh','min'),h1=('hh','max'),aud=('perf_audience','max'))
hol={r[:4]+'-'+r[4:6]+'-'+r[6:] for r in pd.read_csv('holidays.csv',dtype=str).iloc[:,0]}
big=S[(S.aud>=9000)&(S.h0>=15)&(S.h1<=23)&~S.index.isin(hol)];small=set(S.index[S.aud>=3500])
ss=pd.read_csv('checks/subway_shows.csv',encoding='utf-8-sig');ss=ss[ss.date.isin(big.index)].set_index('date');sm=ss.start_est.str[:2].astype(int)*60+ss.start_est.str[3:5].astype(int)
print('시작 시각 분포',ss.start_est.value_counts().to_dict());print('연계자료 h0+1 과 같은 날',int(((sm//60)==(big.h0.reindex(sm.index)+1)).sum()),'/',len(sm))
def bins(t,m):
    return pd.DataFrame({'d':t[m].dt.strftime('%Y-%m-%d'),'b':(t[m].dt.hour*60+t[m].dt.minute)//5}).groupby(['d','b']).size().unstack(fill_value=0).reindex(columns=range(288),fill_value=0)
def base(T):
    wd=pd.to_datetime(T.index).weekday;bm=~T.index.isin(small)&~T.index.isin(hol);return {w:T[bm&(wd==w)].median() for w in range(7)}
m3=ok&g.isin(['북2문','동2문','남2문']);TX=bins(x,m3);bx=base(TX);on={}
for d in big.index:
    if d not in TX.index:continue
    ex=(TX.loc[d]-bx[pd.Timestamp(d).weekday()]).rolling(3).sum().values;lo=(big.h0[d]+1)*12+18;seg=ex[lo:288]
    if len(seg)<6 or np.nanmax(seg)<30:continue
    on[d]=(lo+np.argmax(seg>=0.4*np.nanmax(seg)))*5-10
on=pd.Series(on);dd=(on-sm.reindex(on.index)).dropna();print('시작부터 출차 몰림까지(분)',dd.describe()[['25%','50%','75%']].round().to_dict())
out={'dur':float(dd.median())}
for gate in ('북2문','동2문','남2문'):
    mg=ok&(g==gate);TE=bins(e,mg);TXg=bins(x,mg);be=base(TE);bxg=base(TXg);pre=[];post=[]
    for d in on.index:
        if d not in sm.index or d not in TE.index:continue
        w=pd.Timestamp(d).weekday();s0=int(sm[d]//5);o0=int(on[d]//5)
        a=(TE.loc[d]-be[w]).values;b=(TXg.loc[d]-bxg[w]).values
        if s0-36>=0 and s0+6<=288:pre.append([a[s0+i*2:s0+i*2+2].sum() for i in range(-18,3)])
        if o0-6>=0 and o0+24<=288:post.append([b[o0+i*2:o0+i*2+2].sum() for i in range(-3,12)])
    out[gate]={'in':[round(float(v),1) for v in np.mean(pre,axis=0)],'out':[round(float(v),1) for v in np.mean(post,axis=0)]}
    print(gate,'입차 증가(시작 -180~+20, 10분)',[int(round(v)) for v in out[gate]['in']],'합',int(sum(out[gate]['in'])));print(gate,'출차 증가(몰림 -30~+110)',[int(round(v)) for v in out[gate]['out']],'합',int(sum(out[gate]['out'])))
# 하차 곡선
a=pd.read_csv('서울교통공사_역별 일별 시간대별 승하차인원_20251231.csv',encoding='cp949');a=a[a['역명'].isin(['올림픽공원(한국체대)'])&(a['승하차구분']=='하차')]
hc=[q for q in a.columns if '시간대' in q];A=a.melt(id_vars=['수송일자'],value_vars=hc,var_name='hc',value_name='n');A['h']=A.hc.str[:2].astype(int);A=A.rename(columns={'수송일자':'d'})
b=pd.read_csv('9호선_서울교통공사_9호선2_3단계 역별일별시간대별승하차인원_20251231.csv',encoding='cp949');b=b[b['역사명'].astype(str).str.contains('올림픽공원')&b['구분'].astype(str).str.contains('하차')]
hb=[q for q in b.columns if re.match(r'\d\d시-',q)];B=b.melt(id_vars=['날짜'],value_vars=hb,var_name='hc',value_name='n');B['h']=B.hc.str[:2].astype(int);B=B.rename(columns={'날짜':'d'})
X=pd.concat([A[['d','h','n']],B[['d','h','n']]]);X['n']=pd.to_numeric(X.n.astype(str).str.replace(',',''),errors='coerce').fillna(0);X['d']=X.d.astype(str).str[:10];X=X.groupby(['d','h']).n.sum().unstack(fill_value=0)
xw=pd.to_datetime(X.index).weekday;xb={w:X[~X.index.isin(small)&~X.index.isin(hol)&(xw==w)].median() for w in range(7)}
rows=[]
for d,t in sm.items():
    if d not in X.index:continue
    ex=(X.loc[d]-xb[pd.Timestamp(d).weekday()]).clip(lower=0);h=int(t//60);v=np.array([ex.get(q,0) for q in range(h-5,h+1)],float)
    if v.sum()<800:continue
    rows.append((d,t,v.sum(),v/v.sum()))
print('하차 쓸 수 있는 날',len(rows),'합 중앙',int(np.median([r[2] for r in rows])))
tt=np.arange(-360,61,1.0)
def shares(t0,d0,k,th):
    u=np.clip(d0-tt,0,None);pdf=np.where(u>0,u**(k-1)*np.exp(-u/th),0);pdf=pdf/pdf.sum();h=int(t0//60);return np.array([pdf[(tt>=q*60-t0)&(tt<q*60-t0+60)].sum() for q in range(h-5,h+1)])
grid=[(d0,k,th) for d0 in range(-30,31,5) for k in (1,1.5,2,3,4) for th in (15,25,35,50,70,100)]
fit=lambda R:min(grid,key=lambda p:sum(np.abs(shares(r[1],*p)-r[3]).sum() for r in R))
res={'m':[],'b':[]};idx=range(len(rows));ps=[]
for f in range(4):
    te=[rows[i] for i in idx if i%4==f];tr=[rows[i] for i in idx if i%4!=f];p=fit(tr);ps.append(p);gm=np.mean([r[3] for r in tr],axis=0)
    for r in te:res['m'].append(np.abs(shares(r[1],*p)-r[3]).sum()/2);res['b'].append(np.abs(gm-r[3]).sum()/2)
print('맞춘 값',ps);print('하차 일치율: 10분 모형 %.1f%% | 평균 몫 %.1f%%'%(100-100*np.mean(res['m']),100-100*np.mean(res['b'])))
p=fit(rows);d0,k,th=p;u=np.clip(d0-tt,0,None);pdf=np.where(u>0,u**(k-1)*np.exp(-u/th),0);pdf/=pdf.sum()
out['alight']={'params':p,'share':[round(float(pdf[(tt>=m)&(tt<m+10)].sum())*100,2) for m in range(-180,30,10)],'before180':round(float(pdf[tt<-180].sum())*100,1)};print('하차 10분 몫(-180~+20)',out['alight'])
json.dump(out,open('checks/sim_inputs_2025.json','w'),ensure_ascii=False)
