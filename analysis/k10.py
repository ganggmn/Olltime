import pandas as pd,numpy as np,re,json,warnings;warnings.filterwarnings('ignore')
from math import gamma as G
df=pd.read_csv('inout_2025_full.csv',usecols=['entry_gate','entry_time','exit_time'],encoding='utf-8-sig');e=pd.to_datetime(df.entry_time);x=pd.to_datetime(df.exit_time);st=(x-e).dt.total_seconds()/60
g=df.entry_gate.astype(str).str.split('입구').str[0];ok=(st>=10)&(st<4320)&g.isin(['북2문','동2문','남2문']);xx=x[ok]
L=pd.read_csv('linked_2025.csv',encoding='utf-8-sig',usecols=['datetime','perf_name','perf_audience']);L=L[L.perf_name.notna()&(L.perf_name!='')];L['d']=L.datetime.str[:10];L['hh']=L.datetime.str[11:13].astype(int)
S=L.groupby('d').agg(h0=('hh','min'),h1=('hh','max'),aud=('perf_audience','max'))
hol={r[:4]+'-'+r[4:6]+'-'+r[6:] for r in pd.read_csv('holidays.csv',dtype=str).iloc[:,0]}
big=S[(S.aud>=9000)&(S.h0>=15)&(S.h1<=23)&~S.index.isin(hol)];small=set(S.index[S.aud>=3500])
# 5분 출차
T=pd.DataFrame({'d':xx.dt.strftime('%Y-%m-%d'),'b':(xx.dt.hour*60+xx.dt.minute)//5}).groupby(['d','b']).size().unstack(fill_value=0).reindex(columns=range(288),fill_value=0)
wd=pd.to_datetime(T.index).weekday;basemask=~T.index.isin(small)&~T.index.isin(hol)
base={w:T[basemask&(wd==w)].median() for w in range(7)}
on={}
for d in big.index:
    if d not in T.index:continue
    ex=(T.loc[d]-base[pd.Timestamp(d).weekday()]).rolling(3).sum().values;lo=(big.h0[d]+1)*12+18;seg=ex[lo:288]
    if len(seg)<6 or np.nanmax(seg)<30:continue
    th=0.4*np.nanmax(seg);i=np.argmax(seg>=th);on[d]=(lo+i)*5-10
on=pd.Series(on);print('끝 시각 잡힌 날',len(on),'| 시각 분포(분)',on.describe()[['min','50%','max']].round().to_dict(),'| 정각에서 벗어난 분',((on%60)).round().value_counts(bins=[-1,14,29,44,59]).sort_index().to_dict())
# 역 승차(올림픽공원 5+9)
a=pd.read_csv('서울교통공사_역별 일별 시간대별 승하차인원_20251231.csv',encoding='cp949');a=a[a['역명'].isin(['올림픽공원(한국체대)'])&(a['승하차구분']=='승차')]
hc=[q for q in a.columns if '시간대' in q];A=a.melt(id_vars=['수송일자'],value_vars=hc,var_name='hc',value_name='n');A['h']=A.hc.str[:2].astype(int);A=A.rename(columns={'수송일자':'d'})
b=pd.read_csv('9호선_서울교통공사_9호선2_3단계 역별일별시간대별승하차인원_20251231.csv',encoding='cp949');b=b[b['역사명'].astype(str).str.contains('올림픽공원')&b['구분'].astype(str).str.contains('승차')]
hb=[q for q in b.columns if re.match(r'\d\d시-',q)];B=b.melt(id_vars=['날짜'],value_vars=hb,var_name='hc',value_name='n');B['h']=B.hc.str[:2].astype(int);B=B.rename(columns={'날짜':'d'})
X=pd.concat([A[['d','h','n']],B[['d','h','n']]]);X['n']=pd.to_numeric(X.n.astype(str).str.replace(',',''),errors='coerce').fillna(0);X['d']=X.d.astype(str).str[:10];X=X.groupby(['d','h']).n.sum().unstack(fill_value=0)
xw=pd.to_datetime(X.index).weekday;xb={w:X[~X.index.isin(small)&~X.index.isin(hol)&(xw==w)].median() for w in range(7)}
rows=[]
for d,t in on.items():
    if d not in X.index:continue
    ex=(X.loc[d]-xb[pd.Timestamp(d).weekday()]).clip(lower=0);h=int(t//60);hs=[h-1,h,h+1,h+2];hs=[q for q in hs if q in ex.index]
    v=np.array([ex.get(q,0) for q in [h-1,h,h+1,h+2]],float)
    if v.sum()<800:continue
    rows.append((d,t,h,int(big.h1[d]),v.sum(),v/v.sum()))
print('쓸 수 있는 날',len(rows),'| 승차 증가 합 중앙',int(np.median([r[4] for r in rows])))
tt=np.arange(-120,241,1.0)
def shares(t_on,d0,k,th):
    u=np.clip(tt-d0,0,None);pdf=np.where(u>0,u**(k-1)*np.exp(-u/th),0);pdf=pdf/pdf.sum();h=int(t_on//60);out=[]
    for q in (h-1,h,h+1,h+2):
        lo=q*60-t_on;out.append(pdf[(tt>=lo)&(tt<lo+60)].sum())
    return np.array(out)
grid=[(d0,k,th) for d0 in range(-60,31,5) for k in (1.5,2,3,4,6) for th in (3,5,8,12,18,25)]
def fit(R):
    best=None
    for p in grid:
        err=sum(np.abs(shares(r[1],*p)-r[5]).sum() for r in R)
        if best is None or err<best[0]:best=(err,p)
    return best[1]
idx=np.arange(len(rows));res={'m':[],'b1':[],'b2':[]};ps=[]
for f in range(4):
    te=[rows[i] for i in idx if i%4==f];tr=[rows[i] for i in idx if i%4!=f];p=fit(tr);ps.append(p)
    # 기준 1: 끝난 '시'만 알 때(기관 연계자료의 마지막 공연 시각 기준 평균 몫)
    def bshare(R,key):
        m={}
        for r in R:
            off=r[2]-key(r);m.setdefault(off,[]).append(r[5])
        return {o:np.mean(v,axis=0) for o,v in m.items()},np.mean([r[5] for r in R],axis=0)
    m1,g1=bshare(tr,lambda r:r[3]);
    for r in te:
        res['m'].append(np.abs(shares(r[1],*p)-r[5]).sum()/2);res['b1'].append(np.abs(m1.get(r[2]-r[3],g1)-r[5]).sum()/2);res['b2'].append(np.abs(g1-r[5]).sum()/2)
print('맞춘 값(시작 지연 분, 모양, 폭)',ps)
print('시간대별 몫을 잘못 나눈 비율(%%): 10분 모형 %.1f | 끝난 시(時)만 쓰는 방식 %.1f | 평균 몫만 %.1f'%tuple(100*np.mean(res[k]) for k in ('m','b1','b2')))
print('일치율: 10분 모형 %.1f%% | 시 단위 %.1f%% | 평균 %.1f%%'%tuple(100-100*np.mean(res[k]) for k in ('m','b1','b2')))
p=fit(rows);d0,k,th=p;u=np.clip(tt-d0,0,None);pdf=np.where(u>0,u**(k-1)*np.exp(-u/th),0);pdf/=pdf.sum()
c={int(m):round(float(pdf[(tt>=m)&(tt<m+10)].sum())*100,1) for m in range(-60,120,10)};print('전체로 맞춘 값',p,'| 출차가 몰리기 시작한 시각 기준 10분별 승차 몫(%)',{k:v for k,v in c.items() if v>=0.5})
json.dump({'params':p,'ten_min_share_pct':c,'n_days':len(rows),'err':{k:float(np.mean(v)) for k,v in res.items()}},open('checks/station_10min_kernel_2025.json','w'))
