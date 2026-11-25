import pandas as pd,numpy as np,warnings,json;warnings.filterwarnings('ignore')
P=pd.read_csv('checks/park_population_2025_hourly.csv',encoding='utf-8-sig');P['t']=pd.to_datetime(P.ts);P=P.set_index('t').park_pop
df=pd.read_csv('inout_2025_full.csv',usecols=['entry_time','exit_time'],encoding='utf-8-sig');e=pd.to_datetime(df.entry_time);x=pd.to_datetime(df.exit_time);st=(x-e).dt.total_seconds()/60;ok=(st>=10)&(st<4320)
es=np.sort(e[ok].values);xs=np.sort(x[ok].values);ts=P.index.values+np.timedelta64(30,'m');cars=pd.Series(np.searchsorted(es,ts)-np.searchsorted(xs,ts),index=P.index)
L=pd.read_csv('linked_2025.csv',encoding='utf-8-sig',usecols=['datetime','perf_name','perf_audience']);L=L[L.perf_name.notna()&(L.perf_name!='')];aud=L.groupby(L.datetime.str[:10]).perf_audience.max()
H=pd.read_csv('holidays.csv',dtype=str);hol={r[:4]+'-'+r[4:6]+'-'+r[6:] for r in H.iloc[:,0]}
W=pd.read_csv('weather_asos_108_2025.csv',encoding='utf-8-sig',usecols=['tm','rn','dsnw']);W['d']=W.tm.str[:10];W['h']=W.tm.str[11:13].astype(int);W=W[W.h.between(9,21)];rain=W.groupby('d').rn.sum();snow=W.groupby('d').dsnw.max()
Q=pd.DataFrame({'pop':P,'cars':cars});Q['d']=Q.index.strftime('%Y-%m-%d');Q['h']=Q.index.hour;Q['mo']=Q.index.month;Q=Q[~Q.mo.isin([8,9])&(Q.mo<=10)]
nf=Q[Q.h.isin([3,4])].groupby('d').agg(pn=('pop','median'),cn=('cars','median'));Q=Q.join(nf,on='d');Q['pv']=Q['pop']-Q.pn;Q['cv']=Q.cars-Q.cn;Q['aud']=Q.d.map(aud).fillna(0)
dt=pd.to_datetime(Q.d);wd=dt.dt.weekday.values;dt=dt.reset_index(drop=True);ish=Q.d.isin(hol);off=ish.values|(wd>=5)
longw=ish&(wd<5)   # 평일인데 공휴일 = 연휴에 낀 날
Q['cls']=np.select([(Q.aud>=9000).values,(Q.aud>=1000).values,longw.values,(wd>=5)],['큰 공연','작은 공연','평일 공휴일','주말'],default='평일')
Q['wet']=(Q.d.map(rain).fillna(0)>=5)|(Q.d.map(snow).fillna(0)>0)
D=Q[Q.h.between(9,22)&(Q.cv>100)&(Q.pv>0)].copy()
print(D.groupby('cls').agg(시간=('h','size'),날=('d','nunique')).T.to_string());print('비·눈 날',D[D.wet].d.nunique(),'/',D.d.nunique())
res=[]
for mo in sorted(D.mo.unique()):
    tr=D[D.mo!=mo];te=D[D.mo==mo].copy()
    k1=(tr.pv.sum()/tr.cv.sum())
    kc=tr.groupby('cls').apply(lambda g:g.pv.sum()/g.cv.sum())
    kch=tr.groupby(['cls','h']).apply(lambda g:np.median(g.pv/g.cv))
    kchw=tr.groupby(['cls','h','wet']).apply(lambda g:np.median(g.pv/g.cv) if len(g)>=8 else np.nan)
    te['A']=np.where(te.aud>=1000,5,3)*te.cv
    te['B']=te.cls.map(kc)*te.cv
    te['C']=[kch.get((c,h),kc[c]) for c,h in zip(te.cls,te.h)]*te.cv
    kw=[kchw.get((c,h,w),np.nan) for c,h,w in zip(te.cls,te.h,te.wet)];te['D']=np.where(np.isnan(kw),te.C/te.cv,kw)*te.cv
    res.append(te)
R=pd.concat(res)
def acc(q,c,tot=False):
    if tot:return 100-100*(np.abs(q[c]-q.pv)/q['pop']).mean()
    return 100-100*np.minimum(np.abs(q[c]-q.pv)/q.pv,2).mean()
lab={'A':'고정 3/5','B':'유형별 한 값','C':'유형×시간 표','D':'+비·눈 구분'}
print('\n방문객 수(새벽 바닥 뺀 값) 맞힌 정도 %, 한 달씩 숨기고 검증')
print(f"{'':<10}"+''.join(f"{v:>14}" for v in lab.values()))
for name,q in [('전체',R)]+[(c,R[R.cls==c]) for c in ['평일','주말','평일 공휴일','작은 공연','큰 공연']]+[('비·눈 날',R[R.wet])]:
    print(f"{name:<10}"+''.join(f"{acc(q,c):>14.1f}" for c in lab))
print('공원 전체 인원 기준 정확도:',{lab[c]:round(acc(R,c,True),1) for c in lab})
T=D.groupby(['cls','h']).apply(lambda g:np.median(g.pv/g.cv)).unstack().round(1);print('\n계수표(차 1대당 방문객)');print(T[[9,11,13,15,17,18,19,20,21,22]].to_string())
wetk=D.groupby(['cls','wet']).apply(lambda g:np.median(g.pv/g.cv)).unstack().round(2);print(wetk.to_string())
T.to_csv('checks/people_per_car_table_2025.csv',encoding='utf-8-sig')
