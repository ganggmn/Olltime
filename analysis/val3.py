import pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
D=pd.read_pickle('/tmp/D.pkl')
w=pd.read_csv('weather_asos_108_2025.csv',encoding='utf-8-sig',usecols=['tm','ta','rn','dsnw','hr3Fhsc']);w['tm']=pd.to_datetime(w.tm);w=w.set_index('tm')
w['date']=w.index.date.astype(str);act=w[(w.index.hour>=7)&(w.index.hour<=22)]
dw=pd.DataFrame({'rain':act.groupby('date').rn.sum(),'snow':w.groupby('date').hr3Fhsc.sum(),'snowdep':w.groupby('date').dsnw.max(),'tmax':w.groupby('date').ta.max(),'tmin':w.groupby('date').ta.min()}).fillna(0)
def cats(r):
    c=[]
    if r.snow>0 or (r.snowdep>0 and r.tmax<3): c.append(('눈','많이' if r.snow>=3 else '조금'))
    elif r.rain>=1: c.append(('비','많이' if r.rain>=10 else '조금'))
    if r.tmax>=30: c.append(('더위','심함' if r.tmax>=33 else '보통'))
    if r.tmax<=3: c.append(('추위','심함' if r.tmax<=-2 else '보통'))
    return c
dw['cats']=dw.apply(cats,axis=1)
import collections
cc=collections.Counter(x for d,c in dw.cats.items() if d<'2025-08-01' and d in set(D.date) for x in c);print('1~7월 날씨 일수',dict(cc))
D['dt']=np.where(D.holi==1,6,D.dow);D['part']=np.select([D.h<12,D.h<17],[0,1],2)
days=sorted(D.date.unique());dtype=D.groupby('date').dt.first();mon=D.groupby('date').m.first()
def oh(v,n):
    M=np.zeros((len(v),n));ok=(v>=0)&(v<n);M[np.where(ok)[0],v[ok].astype(int)]=1;return M
def showF(D):
    h=D.h.values;a=D.aud.values;has=(a>0)
    r0=np.where(has,h-D.h0.fillna(0).values+6,-1);r1=np.where(has,h-D.h1.fillna(0).values+6,-1)
    we=(D.dt.values>=5)
    return np.hstack([a[:,None]*oh(r0,14),a[:,None]*oh(r1,12),has[:,None]*oh(r0,14),has[:,None]*oh(r1,12),(a*we)[:,None]*oh(r0,14),(a*we)[:,None]*oh(r1,12)])
SF=showF(D)
def run(TG,use_w=True,use_lag=True,use_show=True,ret=False):
    y=D[TG].values.astype(float);pred=np.zeros(len(y));Wlog={}
    for m in range(1,8):
        te=(D.m.values==m);tr=~te;T=D[tr]
        B=T.groupby(['dt','h'])[TG].mean();base=B.reindex(pd.MultiIndex.from_arrays([D.dt,D.h])).values
        # level from previous 7 days actual
        dayA=pd.Series(y,index=D.index).groupby(D.date.values).sum();dayB=pd.Series(base,index=D.index).groupby(D.date.values).sum()
        ratio=(dayA/dayB)
        lvl={}
        for i,d in enumerate(days):
            prev=[ratio[x] for x in days[max(0,i-7):i]]
            lvl[d]=float(np.clip(np.mean(prev),0.6,1.4)) if (prev and use_lag) else 1.0
        L=D.date.map(lvl).values;p=base*L
        if use_w:
            # double weights: kind -> intensity, per daypart
            R=pd.DataFrame({'a':y,'p':p,'date':D.date.values,'part':D.part.values})[tr].groupby(['date','part']).sum();R['r']=R.a/R.p
            R=R.reset_index();norm=R[~R.date.map(lambda d:len(dw.cats[d])>0)].groupby('part').r.mean()
            W={}
            for part in range(3):
                Rp=R[R.part==part].set_index('date').r/norm[part]
                for kind in ('비','눈','더위','추위'):
                    dk=[d for d in Rp.index if any(c[0]==kind for c in dw.cats[d]) and len(dw.cats[d])==1 or (any(c[0]==kind for c in dw.cats[d]) and kind in('비','눈'))]
                    n=len(dk);wk=1+(Rp[dk].mean()-1)*n/(n+3) if n else 1.0
                    for inten in ('조금','많이','보통','심함'):
                        di=[d for d in dk if (kind,inten) in dw.cats[d]];ni=len(di)
                        W[(kind,inten,part)]=wk+(Rp[di].mean()-wk)*ni/(ni+3) if ni else wk
            f=np.ones(len(D));dc=D.date.map(dw.cats).values;pt=D.part.values
            for i in np.where(te|tr)[0]:
                for c in dc[i]: f[i]*=W[(c[0],c[1],pt[i])]
            p=p*f;Wlog[m]=W
        if use_show:
            res=y-p;A=SF;beta=np.linalg.solve(A[tr].T@A[tr]+3*np.eye(A.shape[1]),A[tr].T@res[tr]);p=p+A@beta
        pred[te]=np.maximum(p[te],0)
    day=(D.h.values>=7);acc=lambda mk:round(100*(1-np.abs(pred-y)[mk].sum()/y[mk].sum()),1)
    out=[acc(day)]+[acc(day&(D.m.values==m)) for m in range(1,8)]
    return (out,pred,Wlog) if ret else out
for TG,lab in (('O','주차장 안 차량'),('E','시간당 입차'),('X','시간당 출차')):
    print('\n'+lab,'| 전체, 1~7월')
    print(' 요일·공휴일만     ',run(TG,0,0,0));print(' +날씨(종류×세기)  ',run(TG,1,0,0));print(' +공연             ',run(TG,1,0,1));print(' +지난주 실측      ',run(TG,1,1,1));print(' (날씨 빼고 전부)  ',run(TG,0,1,1))
o,p,W=run('E',1,1,1,True)
print('\n입차 날씨 가중치(전체 달 평균): 오전/오후/저녁')
for k in [('비','조금'),('비','많이'),('눈','조금'),('눈','많이'),('더위','보통'),('더위','심함'),('추위','보통'),('추위','심함')]:
    print(k,[round(float(np.mean([W[m][(k[0],k[1],pt)] for m in W])),2) for pt in range(3)])
dw.to_pickle('/tmp/dw.pkl')
