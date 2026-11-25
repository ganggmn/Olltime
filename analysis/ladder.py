import os,sys,numpy as np,pandas as pd,warnings;warnings.filterwarnings('ignore')
src=open(os.path.expanduser('~/val6.py'),encoding='utf-8').read()
a=src.index("dw=pd.read_pickle");b=src.index("L=pd.read_csv('linked_2025.csv'");c=src.index("def wc(d,mode)");d_=src.index("days=sorted(D.date.unique())");e_=src.index("for TG,lab in")
code=src[:a]+src[b:c]+"def wc(d,mode): return []\n"+src[d_:e_].replace("print('일수: 추위',collections.Counter(c for d in days for c in wc(d,1)))","")
if len(sys.argv)>1:code=code.replace("df=df[~df.entry_gate.str.contains('CMB')];e=pd.to_datetime(df.entry_time);x=pd.to_datetime(df.exit_time)","df=df[~df.entry_gate.str.contains('CMB')];_st=(pd.to_datetime(df.exit_time)-pd.to_datetime(df.entry_time)).dt.total_seconds()/60;df=df[_st>=10];e=pd.to_datetime(df.entry_time);x=pd.to_datetime(df.exit_time)")
exec(code)
y=D['O'].values.astype(float);EV=[1,2,3,4,5,6,7,10];day=D.h.values>=7
D['g1']=0;D['g2']=np.select([D.dow<4,D.dow==4,D.dow==5],[0,1,2],3)
def ladder(col,show,lag,forward=False):
    pred=np.full(len(y),np.nan)
    for m in MONTHS:
        te=(D.m.values==m);tr=(D.m.values<m) if forward else ~te
        if tr.sum()<24*20:continue
        T=D[tr];B=T.groupby([col,'h']).O.mean();base=B.reindex(pd.MultiIndex.from_arrays([D[col],D.h])).values
        if np.isnan(base).any():
            B0=T.groupby(['g2','h']).O.mean();b0=B0.reindex(pd.MultiIndex.from_arrays([D.g2,D.h])).values;base=np.where(np.isnan(base),b0,base)
        p=base.copy()
        if lag:
            dayA=pd.Series(y,index=D.index).groupby(D.date.values).sum();dayB=pd.Series(base,index=D.index).groupby(D.date.values).sum();ratio=dayA/dayB;lvl={}
            for i,d in enumerate(days):
                prev=[ratio[x] for x in days[max(0,i-7):i] if not (col=='dt1' and x in MJ)];lvl[d]=float(np.clip(np.mean(prev),0.6,1.4)) if prev else 1.0
            p=base*D.date.map(lvl).values
        if show:
            res=y-p;beta=np.linalg.solve(SF[tr].T@SF[tr]+3*np.eye(SF.shape[1]),SF[tr].T@res[tr]);p=p+SF@beta
        pred[te]=np.maximum(p[te],0)
    return pred
def rep(lab,pred,months=EV):
    mk=day&np.isin(D.m.values,months)&~np.isnan(pred);e=np.abs(pred-y)[mk];acc=100*(1-e.sum()/y[mk].sum());mean=y[mk].mean()
    print('%-28s 정확도 %.1f | 평균 오차 %.0f대 | 가운데 %.0f대 | 실제 평균 %.0f대 | 역산 %.0f대 | 시각별 오차율 평균 방식 %.1f%% | %d시간'%(lab,acc,e.mean(),np.median(e),mean,(1-acc/100)*mean,100-100*(e/np.maximum(y[mk],1)).mean(),mk.sum()));return pred
print('모드',sys.argv[1:] or '전체 차량','| 채점 달',EV)
rep('시간대만',ladder('g1',0,0));rep('+요일',ladder('g2',0,0));rep('+공휴일·명절',ladder('dt1',0,0));rep('+공연',ladder('dt1',1,0));P=rep('+지난 7일',ladder('dt1',1,1))
rep('  (같은 예측, 12개월 전체)',P,MONTHS);rep('  (같은 예측, 8~9월 복원)',P,[8,9])
rep('앞선 달로만 배움(3~7,10월)',ladder('dt1',1,1,True),[3,4,5,6,7,10]);rep('  비교: 같은 달, 원래 방식',P,[3,4,5,6,7,10])
# 2시간·1시간 전 실제 값 보정: 남은 차이를 그대로 옮김
for hh in (6,4,2,1):
    r=pd.Series(y-P,index=D.index);prev=r.reindex(D.index-pd.Timedelta(hours=hh)).values;Q=np.where(np.isnan(prev),P,np.maximum(P+prev,0));rep('+%d시간 전 실제 값'%hh,Q)
# 덜 맞는 날
dv=D.date.values;mjm=np.isin(dv,list(MJ));whm=np.array([(d in hol) for d in dv])&(D.dow.values<5)&~mjm
for lab,mk0 in (('설·추석(%d일)'%len(set(dv[mjm])),mjm),('평일 공휴일(%d일)'%len(set(dv[whm])),whm),('그 밖의 날',~mjm&~whm)):
    mk=day&mk0&~np.isnan(P);e=np.abs(P-y)[mk];print(lab,'정확도 %.1f | 평균 오차 %.0f대 | %d시간'%(100*(1-e.sum()/y[mk].sum()),e.mean(),mk.sum()))
