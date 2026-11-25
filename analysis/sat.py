import pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
df=pd.read_csv('inout_2025_full.csv',usecols=['entry_gate','entry_time','exit_gate','exit_time'],encoding='utf-8-sig')
x=pd.to_datetime(df.exit_time);e=pd.to_datetime(df.entry_time);g=df.exit_gate.astype(str).str.split('출구').str[0].str.split('입구').str[0]
ok=(x>=e)&~x.dt.month.isin([8,9]);x=x[ok];g=g[ok];e=e[ok]
print(g.value_counts().head(8).to_dict())
L=pd.read_csv('linked_2025.csv',encoding='utf-8-sig',usecols=['datetime','perf_name','perf_audience']);L=L[L.perf_name.notna()&(L.perf_name!='')];L['d']=L.datetime.str[:10];L['hh']=L.datetime.str[11:13].astype(int)
S=L.groupby('d').agg(h1=('hh','max'),aud=('perf_audience','max'));big=[d for d in S.index[S.aud>=9000] if d[5:7] not in('08','09') and not(d[5:7]=='11' and int(d[8:])>6) and not(d[5:7]=='12' and int(d[8:])>7)]
t=pd.DataFrame({'g':g,'s':x.dt.floor('5min'),'d':x.dt.strftime('%Y-%m-%d'),'h':x.dt.hour})
c=t.groupby(['g','d','s']).size().rename('n').reset_index()
for gate in ['북2문','동2문','남2문','서2문']:
    cg=c[c.g==gate];cap=cg.n.quantile(.999);mx=cg.n.max()
    ev=cg[cg.d.isin(big)&(cg.s.dt.hour>=19)]
    per=ev.groupby('d').apply(lambda q:pd.Series({'pk':q.n.max(),'sat':(q.n>=0.8*cap).sum()*5,'tot':q.n.sum()}))
    print(gate,'5분 최대',mx,'상위0.1%',round(cap),'| 공연날',len(per),'일: 저녁 5분 최대 중앙',per.pk.median(),'| 상한 80% 이상인 시간(분) 중앙',per.sat.median(),'최대',per.sat.max(),'| 19시 이후 출차 중앙',per.tot.median())
# 가장 심한 날 한 문의 5분 단위 출차
ev=c[c.d.isin(big)&(c.s.dt.hour>=20)];w=ev.groupby(['d','g']).n.sum().sort_values(ascending=False).head(3);print(w)
d0,g0=w.index[0];q=c[(c.d==d0)&(c.g==g0)&(c.s.dt.hour>=20)];print(d0,g0,' '.join(f"{s.strftime('%H:%M')}={n}" for s,n in zip(q.s,q.n)))
