import pandas as pd,numpy as np
D=pd.read_pickle('/tmp/D.pkl')
print('주차장 안 차량: 낮 평균',round(D[D.h.between(10,20)].O.mean()),'최대',D.O.max())
for t in 'OEX':
    s_=D[t].astype(float)
    lw=s_.reindex(D.index-pd.Timedelta('7D')).values
    L7=np.vstack([s_.reindex(D.index-pd.Timedelta(days=k)).values for k in range(1,8)])
    m7=np.nanmean(L7,axis=0);hm=D.groupby('h')[t].transform('mean').values
    m7=np.where(np.isnan(m7),hm,m7);lw=np.where(np.isnan(lw),m7,lw)
    D['lag_'+t+'_w']=lw;D['lag_'+t+'_7']=m7
def oh(v,n): 
    M=np.zeros((len(v),n));ok=(v>=0)&(v<n);M[np.where(ok)[0],v[ok].astype(int)]=1;return M
def feats(D,level):
    h=D.h.values;F=[oh(h,24)]
    if level>=1:
        F.append(oh(D.dow.values*24+h,168))
    if level>=2:
        hd=D.holi.values[:,None]*oh(h,24);F.append(hd)
    if level>=3:
        wet=(D.rsum.values>=1)[:,None]*oh(h,24);F.append(wet)
        F.append(np.minimum(D.rain3.values,10)[:,None]*oh(h//3,8))
        t=(D.tmax.values-15)/10;F.append(t[:,None]*oh(h//3,8));F.append((t**2)[:,None]*oh(h//3,8))
        F.append(((D.dow.values>=5)|(D.holi.values==1))[:,None]*(D.rsum.values>=1)[:,None]*oh(h,24))
    if level>=4:
        a=D.aud.values;has=(a>0)
        r0=np.where(has,h-D.h0.fillna(0).values+6,-1);r1=np.where(has,h-D.h1.fillna(0).values+6,-1)
        F.append(a[:,None]*oh(r0,14));F.append(a[:,None]*oh(r1,12));F.append(has[:,None]*oh(r0,14));F.append(has[:,None]*oh(r1,12))
        we=((D.dow.values>=5)|(D.holi.values==1))
        F.append((a*we)[:,None]*oh(r0,14));F.append((a*we)[:,None]*oh(r1,12))
    if level>=5:
        F.append(D[['lag_'+TG+'_w','lag_'+TG+'_7']].values/100.0)
        F.append((D['lag_'+TG+'_7'].values/100.0)[:,None]*oh(h//3,8))
    return np.hstack(F)
def fit(A,y,lam=3.0):
    return np.linalg.solve(A.T@A+lam*np.eye(A.shape[1]),A.T@y)

names=['시간대만','+요일','+공휴일','+날씨','+공연 정보','+지난주 실측']
summ={}
for TG,lab in (('O','주차장 안 차량'),('E','시간당 입차'),('X','시간당 출차')):
    y=D[TG].values.astype(float);print('\n'+lab+' | 정확도% : 전체 / 큰 공연 날 / 공연 전후 시간  (평균오차 대)')
    for lv in range(6):
        A=feats(D,lv);pred=np.zeros(len(y))
        for m in range(1,8):
            te=(D.m.values==m);pred[te]=A[te]@fit(A[~te],y[~te])
        pred=np.maximum(pred,0);day=(D.h.values>=7)
        showd=(D.aud.values>=0.8)&day
        win=showd&(D.h.values>=D.h0.fillna(99).values-3)&(D.h.values<=D.h1.fillna(-9).values+1)
        f=lambda mk:(round(100*(1-np.abs(pred-y)[mk].sum()/y[mk].sum()),1),round(np.abs(pred-y)[mk].mean()))
        print(names[lv],f(day),f(showd),f(win))
        if lv==5:
            D['p'+TG]=pred
            for m in range(1,8):
                mk=day&(D.m.values==m);print('  ',m,'월',f(mk)[0],end='')
            print()
D.to_pickle('/tmp/D2.pkl')
