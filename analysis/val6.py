import pandas as pd,numpy as np,warnings,collections;warnings.filterwarnings('ignore')
df=pd.read_csv('inout_2025_full.csv',usecols=['entry_gate','entry_time','exit_time'],encoding='utf-8-sig')
df=df[~df.entry_gate.str.contains('CMB')];e=pd.to_datetime(df.entry_time);x=pd.to_datetime(df.exit_time)
idx=pd.date_range('2025-01-01','2025-12-08',freq='h',inclusive='left')
E=e.dt.floor('h').value_counts().reindex(idx,fill_value=0).astype(float);X=x.dt.floor('h').value_counts().reindex(idx,fill_value=0).astype(float)
es=np.sort(e.values);xs=np.sort(x.values);half=(idx+pd.Timedelta('30min')).values
O=pd.Series(np.searchsorted(es,half)-np.searchsorted(xs,half),index=idx).astype(float)
D=pd.DataFrame({'E':E,'X':X,'O':O});D['date']=D.index.date.astype(str);D['h']=D.index.hour;D['m']=D.index.month
for m,r in ((8,.2247),(9,.232)): D.loc[D.m==m,['E','X','O']]/=r
bad={'2025-01-31','2025-02-28','2025-03-31','2025-04-30','2025-05-31','2025-06-30','2025-07-31','2025-08-31','2025-09-30','2025-10-31'}
D=D[~D.date.isin(bad)&~((D.m==11)&(D.index.day>6))&~((D.m==12)&(D.index.day>7))]
hol={r[:4]+'-'+r[4:6]+'-'+r[6:] for r in pd.read_csv('holidays.csv',dtype=str).iloc[:,0]}
D['dow']=D.index.dayofweek;D['dt0']=np.where(D.date.isin(hol),6,D.dow)
MJ={'2025-01-28':7,'2025-01-29':8,'2025-01-30':9,'2025-10-05':7,'2025-10-06':8,'2025-10-07':9}
D['dt1']=D.date.map(MJ).fillna(D.dt0).astype(int)
dw=pd.read_pickle('/tmp/dw.pkl')
L=pd.read_csv('linked_2025.csv',encoding='utf-8-sig',usecols=['datetime','perf_name','perf_audience']);L=L[L.perf_name.notna()&(L.perf_name!='')]
L['date']=L.datetime.str[:10];L['hh']=L.datetime.str[11:13].astype(int)
S=L.groupby('date').agg(h0=('hh','min'),h1=('hh','max'),aud=('perf_audience','max'));S['h1']+=1
D=D.join(S,on='date');D['aud']=D.aud.fillna(0)/10000;D['part']=np.select([D.h<12,D.h<17],[0,1],2)
def wc(d,mode):
    r=dw.loc[d];m=int(d[5:7]);c=[]
    if mode>=1:
        if m in(12,1,2) and r.tmax<=3: c.append(('추위','심함' if r.tmax<=-2 else '보통'))
        if m in(7,8,9) and r.tmax>=31: c.append(('더위','심함' if r.tmax>=34 else '보통'))
    if mode>=2:
        if r.snow>0: c.append(('눈','많이' if r.snow>=3 else '조금'))
        elif r.rain>=1: c.append(('비','많이' if r.rain>=10 else '조금'))
    return c
days=sorted(D.date.unique())
print('일수: 추위',collections.Counter(c for d in days for c in wc(d,1)))
def season(d):
    m=int(d[5:7]);return 'W' if m in(12,1,2) else 'S' if m in(7,8,9) else 'N'
def oh(v,n):
    M=np.zeros((len(v),n));ok=(v>=0)&(v<n);M[np.where(ok)[0],v[ok].astype(int)]=1;return M
h=D.h.values;a=D.aud.values;has=(a>0);r0=np.where(has,h-D.h0.fillna(0).values+6,-1);r1=np.where(has,h-D.h1.fillna(0).values+6,-1);we=(D.dt0.values>=5)
SF=np.hstack([a[:,None]*oh(r0,14),a[:,None]*oh(r1,12),has[:,None]*oh(r0,14),has[:,None]*oh(r1,12),(a*we)[:,None]*oh(r0,14),(a*we)[:,None]*oh(r1,12)])
MONTHS=[1,2,3,4,5,6,7,8,9,10,11,12]
def run(TG,dtcol='dt0',wmode=0,ret=False):
    y=D[TG].values;pred=np.zeros(len(y));Wl={}
    cats={d:wc(d,wmode) for d in days}
    for m in MONTHS:
        te=(D.m.values==m);tr=~te;T=D[tr]
        B=T.groupby([dtcol,'h'])[TG].mean();base=B.reindex(pd.MultiIndex.from_arrays([D[dtcol],D.h])).values
        if np.isnan(base).any():
            B0=T.groupby(['dt0','h'])[TG].mean();b0=B0.reindex(pd.MultiIndex.from_arrays([D.dt0,D.h])).values;base=np.where(np.isnan(base),b0,base)
        dayA=pd.Series(y,index=D.index).groupby(D.date.values).sum();dayB=pd.Series(base,index=D.index).groupby(D.date.values).sum();ratio=dayA/dayB
        lvl={}
        for i,d in enumerate(days):
            prev=[ratio[x] for x in days[max(0,i-7):i] if not (dtcol=='dt1' and x in MJ)]
            lvl[d]=float(np.clip(np.mean(prev),0.6,1.4)) if prev else 1.0
        p=base*D.date.map(lvl).values
        if wmode:
            R=pd.DataFrame({'a':y,'p':p,'date':D.date.values,'part':D.part.values})[tr].groupby(['date','part']).sum().reset_index();R['r']=R.a/R.p
            R['sea']=R.date.map(season);R['n']=R.date.map(lambda d:len(cats[d]));W={}
            for part in range(3):
                Rp=R[R.part==part].set_index('date')
                for kind,sea in (('추위','W'),('더위','S'),('눈',None),('비',None)):
                    pool=Rp if sea is None else Rp[Rp.sea==sea]
                    nm=pool[pool.n==0].r.mean() if (pool.n==0).any() else Rp[Rp.n==0].r.mean()
                    dk=[d for d in pool.index if any(c[0]==kind for c in cats[d])];n=len(dk)
                    wk=1+((pool.r[dk]/nm).mean()-1)*n/(n+3) if n else 1.0
                    for it in ('조금','많이','보통','심함'):
                        di=[d for d in dk if (kind,it) in cats[d]];ni=len(di)
                        W[(kind,it,part)]=wk+((pool.r[di]/nm).mean()-wk)*ni/(ni+3) if ni else wk
            f=np.ones(len(D));pt=D.part.values;dv=D.date.values
            for i in range(len(D)):
                for c in cats[dv[i]]: f[i]*=W[(c[0],c[1],pt[i])]
            p=p*f;Wl[m]=W
        res=y-p;beta=np.linalg.solve(SF[tr].T@SF[tr]+3*np.eye(SF.shape[1]),SF[tr].T@res[tr]);p=p+SF@beta
        pred[te]=np.maximum(p[te],0)
    day=(D.h.values>=7);acc=lambda mk:round(float(100*(1-np.abs(pred-y)[mk].sum()/y[mk].sum())),1)
    out=[acc(day)]+[acc(day&(D.m.values==m)) for m in MONTHS]
    mj=acc(day&D.date.isin(MJ).values)
    return (out,mj,pred,Wl) if ret else (out,mj)
for TG,lab in (('O','주차장 안 차량'),('E','시간당 입차'),('X','시간당 출차')):
    print('\n'+lab,'| 전체, 1..12월 | 명절 6일')
    print(' A 기본(명절=일요일)      ',*run(TG,'dt0',0))
    print(' B 명절 따로              ',*run(TG,'dt1',0))
    print(' C B+추위(12~2)·더위(7~9) ',*run(TG,'dt1',1))
    print(' D C+비·눈                ',*run(TG,'dt1',2))
o,mj,p,W=run('E','dt1',2,True)
print('\n입차 가중치 오전/오후/저녁')
for k in [('추위','보통'),('추위','심함'),('더위','보통'),('더위','심함'),('비','조금'),('비','많이'),('눈','조금'),('눈','많이')]:
    print(k,[round(float(np.mean([W[m][(k[0],k[1],pt)] for m in W])),2) for pt in range(3)])
dd=D.groupby('date').E.sum()
print('명절 하루 차량',{d:int(dd[d]) for d in ['2025-01-27','2025-01-28','2025-01-29','2025-01-30','2025-10-05','2025-10-06','2025-10-07','2025-10-08']})
print('평소 일요일 평균',int(D[(D.dt0==6)&~D.date.isin(MJ)].groupby('date').E.sum().mean()))
Y=D[D.date.isin(MJ)];print('명절 시간대별 입차 비중 피크시', Y.groupby('h').E.mean().idxmax(), '평소 일요일', D[(D.dt0==6)&~D.date.isin(MJ)].groupby('h').E.mean().idxmax())
