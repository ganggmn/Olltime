import pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
df=pd.read_csv('inout_2025_full.csv',usecols=['entry_gate','entry_time','exit_time'],encoding='utf-8-sig')
df=df[~df.entry_gate.str.contains('CMB')];e=pd.to_datetime(df.entry_time);x=pd.to_datetime(df.exit_time)
idx=pd.date_range('2025-05-01','2025-10-31',freq='h',inclusive='left')
E=e.dt.floor('h').value_counts().reindex(idx,fill_value=0);X=x.dt.floor('h').value_counts().reindex(idx,fill_value=0)
es=np.sort(e.values);xs=np.sort(x.values);half=(idx+pd.Timedelta('30min')).values
O=pd.Series(np.searchsorted(es,half)-np.searchsorted(xs,half),index=idx)
D=pd.DataFrame({'E':E,'X':X,'O':O});D['date']=D.index.date.astype(str);D['h']=D.index.hour;D['m']=D.index.month
D=D[~D.date.isin({'2025-05-31','2025-06-30','2025-07-31','2025-08-31','2025-09-30'})]
hol={r[:4]+'-'+r[4:6]+'-'+r[6:] for r in pd.read_csv('holidays.csv',dtype=str).iloc[:,0]}
D['dt']=np.where(D.date.isin(hol),6,D.index.dayofweek)
L=pd.read_csv('linked_2025.csv',encoding='utf-8-sig',usecols=['datetime','perf_name','perf_audience']);L=L[L.perf_name.notna()&(L.perf_name!='')]
L['date']=L.datetime.str[:10];aud=L.groupby('date').perf_audience.max()
D['aud']=D.date.map(aud).fillna(0)
tr=D[D.m.isin([6,7,10])];S=D[D.m.isin([8,9])].copy()
# 1) 표본이 시간대에 고르게 뽑혔는지
shT=tr.groupby('h').E.sum()/tr.E.sum();shS=S.groupby('h').E.sum()/S.E.sum()
print('시간대 분포 상관(입차)',round(np.corrcoef(shT,shS)[0,1],4),'최대 차이 %p',round(100*np.abs(shT-shS).max(),2))
print('표본 체류시간 중앙(분) 8~9월 vs 6·7·10월:',end=' ')
st=(x-e).dt.total_seconds()/60;mm=e.dt.month
print(round(st[mm.isin([8,9])].median()),round(st[mm.isin([6,7,10])].median()))
# 2) 모델(요일×시간, 6·7·10월) 대비 일별 비율
for TG in 'E':
    B=tr.groupby(['dt','h'])[TG].mean();S['p']=B.reindex(pd.MultiIndex.from_arrays([S.dt,S.h])).values
    dd=S.groupby('date').agg(s=(TG,'sum'),p=('p','sum'),aud=('aud','max'),m=('m','first'));dd['r']=dd.s/dd.p
    for m in (8,9):
        q=dd[dd.m==m];print(m,'월 표본비율 추정',round(q.s.sum()/q.p.sum(),3),'| 일별 비율 중앙',round(q.r.median(),3),'표준편차',round(q.r.std(),3),'| 복원 하루 평균',round(q.s.sum()/(q.s.sum()/q.p.sum())/len(q)))
    print('공연 큰 날 비율',round(dd[dd.aud>=8000].r.mean(),3),'없는 날',round(dd[dd.aud==0].r.mean(),3))
# 3) 복원 파일
rate={m:S[S.m==m].E.sum()/S[S.m==m].p.sum() for m in (8,9)}
S['rate']=S.m.map(rate)
out=pd.DataFrame({'datetime':S.index.strftime('%Y-%m-%d %H:00'),'sample_entries':S.E,'sample_exits':S.X,'sample_inside':S.O,
 'est_entries':(S.E/S.rate).round().astype(int),'est_exits':(S.X/S.rate).round().astype(int),'est_inside':(S.O/S.rate).round().astype(int),'sampling_rate_est':S.rate.round(4)})
out.to_csv('checks/restored_2025_08_09_hourly.csv',index=False,encoding='utf-8-sig');print(len(out),'줄 저장');print(out.iloc[40:43].to_string())
print('6·7·10월 하루 평균',round(tr.groupby('date').E.sum().mean()))
