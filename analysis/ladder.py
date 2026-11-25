import os,sys,numpy as np,pandas as pd,warnings;warnings.filterwarnings('ignore')
src=open(os.path.expanduser('~/val6.py'),encoding='utf-8').read()
a=src.index("dw=pd.read_pickle");b=src.index("L=pd.read_csv('linked_2025.csv'");c=src.index("def wc(d,mode)");d_=src.index("days=sorted(D.date.unique())");e_=src.index("for TG,lab in")
code=src[:a]+src[b:c]+"def wc(d,mode): return []\n"+src[d_:e_].replace("print('일수: 추위',collections.Counter(c for d in days for c in wc(d,1)))","")
if len(sys.argv)>1:code=code.replace("df=df[~df.entry_gate.str.contains('CMB')];e=pd.to_datetime(df.entry_time);x=pd.to_datetime(df.exit_time)","df=df[~df.entry_gate.str.contains('CMB')];_st=(pd.to_datetime(df.exit_time)-pd.to_datetime(df.entry_time)).dt.total_seconds()/60;df=df[_st>=10];e=pd.to_datetime(df.entry_time);x=pd.to_datetime(df.exit_time)")
# 입력 검사: 시각을 읽지 못한 행은 세고 빼요(예전에는 한 행만 틀려도 멈췄어요). 출차가 입차보다 이른 행, 입·출차 시각이 같은 행도 세어 둬요.
_P="e=pd.to_datetime(df.entry_time);x=pd.to_datetime(df.exit_time)"
assert _P in code
code=code.replace(_P,"e=pd.to_datetime(df.entry_time,errors='coerce');x=pd.to_datetime(df.exit_time,errors='coerce');_ok=e.notna()&x.notna();BADT=int((~_ok).sum());e=e[_ok];x=x[_ok];NEG=int((x<e).sum());ZERO=int((x==e).sum());NROW=int(len(e))",1)
exec(code)
print('자료 상태: 읽은 행 %d, 시각을 읽지 못해 뺀 행 %d, 출차가 입차보다 이른 행 %d, 입·출차 시각이 같은 행 %d'%(NROW,BADT,NEG,ZERO))
y=D['O'].values.astype(float);EV=[1,2,3,4,5,6,7,10];day=D.h.values>=7
D['g1']=0;D['g2']=np.select([D.dow<4,D.dow==4,D.dow==5],[0,1,2],3)
# 공연 입력: 관객 수(공연 뒤에 기록된 값)를 쓰는 것과, 미리 알 수 있는 공연 유무·시각만 쓰는 것
SF_PRE=SF[:,SF.shape[1]//3:SF.shape[1]*2//3]  # has×시작 기준, has×끝 기준 (관객 수를 곱하지 않은 부분)
dd=pd.to_datetime(pd.Series(days));DIDX={d:i for i,d in enumerate(days)}
def ladder(col,show,lag,forward=False,sf=None):
    SFx=SF if sf is None else sf
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
                # 달력으로 7일 안의 날만(빠진 날이 있어도 더 멀리 가지 않음). 시험 달이 아닌 날은 시험 달의 실제 값을 쓰지 않음
                t0=dd[i]-pd.Timedelta(days=7);own=int(d[5:7])==m
                prev=[ratio[x] for x in days[max(0,i-7):i] if pd.Timestamp(x)>=t0 and not (col=='dt1' and x in MJ) and (own or int(x[5:7])!=m)];lvl[d]=float(np.clip(np.mean(prev),0.6,1.4)) if prev else 1.0
            p=base*D.date.map(lvl).values
        if show:
            res=y-p;beta=np.linalg.solve(SFx[tr].T@SFx[tr]+3*np.eye(SFx.shape[1]),SFx[tr].T@res[tr]);p=p+SFx@beta
        pred[te]=np.maximum(p[te],0)
    return pred
def rep(lab,pred,months=EV):
    mk=day&np.isin(D.m.values,months)&~np.isnan(pred);e=np.abs(pred-y)[mk];acc=100*(1-e.sum()/y[mk].sum());mean=y[mk].mean()
    print('%-28s 정확도 %.1f | 평균 오차 %.0f대 | 중앙값 %.0f대 | 실제 평균 %.0f대 | 역산 %.0f대 | 시각별 오차율 평균 방식 %.1f%% | %d시간'%(lab,acc,e.mean(),np.median(e),mean,(1-acc/100)*mean,100-100*(e/np.maximum(y[mk],1)).mean(),mk.sum()));return pred
print('모드',sys.argv[1:] or '전체 차량','| 채점 달',EV)
rep('시간대만',ladder('g1',0,0));rep('+요일',ladder('g2',0,0));rep('+공휴일·명절',ladder('dt1',0,0));rep('+공연',ladder('dt1',1,0));P=rep('+지난 7일',ladder('dt1',1,1))
rep('  (같은 예측, 12개월 전체)',P,MONTHS);rep('  (같은 예측, 8~9월 복원)',P,[8,9])
rep('앞선 달로만 배움(3~7,10월)',ladder('dt1',1,1,True),[3,4,5,6,7,10]);rep('  비교: 같은 달, 원래 방식',P,[3,4,5,6,7,10])
rep('  앞선 달 + 관객 수 없이(미리 아는 공연 유무·시각만)',ladder('dt1',1,1,True,SF_PRE),[3,4,5,6,7,10]);rep('  같은 달, 관객 수 없이',ladder('dt1',1,1,False,SF_PRE),[3,4,5,6,7,10]);rep('관객 수 없이, 채점 달 전체',ladder('dt1',1,1,False,SF_PRE))
# 2시간·1시간 전 실제 값 보정: 남은 차이를 그대로 옮김
for hh in (6,4,2,1):
    r=pd.Series(y-P,index=D.index);prev=r.reindex(D.index-pd.Timedelta(hours=hh)).values;Q=np.where(np.isnan(prev),P,np.maximum(P+prev,0));rep('+%d시간 전 실제 값'%hh,Q)
# 덜 맞는 날
dv=D.date.values;mjm=np.isin(dv,list(MJ));whm=np.array([(d in hol) for d in dv])&(D.dow.values<5)&~mjm
for lab,mk0 in (('설·추석(%d일)'%len(set(dv[mjm])),mjm),('평일 공휴일(%d일)'%len(set(dv[whm])),whm),('그 밖의 날',~mjm&~whm)):
    mk=day&mk0&~np.isnan(P);e=np.abs(P-y)[mk];print(lab,'정확도 %.1f | 평균 오차 %.0f대 | %d시간'%(100*(1-e.sum()/y[mk].sum()),e.mean(),mk.sum()))
