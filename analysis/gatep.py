import pandas as pd,numpy as np,json,warnings;warnings.filterwarnings('ignore')
df=pd.read_csv('inout_2025_full.csv',usecols=['entry_gate','entry_time','exit_time'],encoding='utf-8-sig');e=pd.to_datetime(df.entry_time);x=pd.to_datetime(df.exit_time);st=(x-e).dt.total_seconds()/60
g=df.entry_gate.astype(str).str.split('입구').str[0];ok=(st>=10)&(st<4320)
L=pd.read_csv('linked_2025.csv',encoding='utf-8-sig',usecols=['datetime','perf_name','perf_audience']);L=L[L.perf_name.notna()&(L.perf_name!='')];aud=L.groupby(L.datetime.str[:10]).perf_audience.max()
hol={r[:4]+'-'+r[4:6]+'-'+r[6:] for r in pd.read_csv('holidays.csv',dtype=str).iloc[:,0]}
days=[d.strftime('%Y-%m-%d') for d in pd.date_range('2025-01-02','2025-10-30')];days=[d for d in days if d[5:7] not in('08','09') and d[8:] not in('28','29','30','31')]
def cls(d):
    wd=pd.Timestamp(d).weekday();c='hol' if (d in hol or wd==6) else 'sat' if wd==5 else 'fri' if wd==4 else 'wk'
    return c+('_show' if aud.get(d,0)>=9000 else '')
C={};[C.setdefault(cls(d),[]).append(d) for d in days];print({k:len(v) for k,v in C.items()})
slots=[(h,m) for h in range(24) for m in (0,20,40)]
G=['북2문','동2문','남2문','서2문','남4문','서1문','남3문'];out={'slots_min':[h*60+m for h,m in slots],'n':{k:len(v) for k,v in C.items()},'gates':{}}
for gate in G:
    m=ok&(g==gate);es=np.sort(e[m].values);xs=np.sort(x[m].values);out['gates'][gate]={}
    for k,ds in C.items():
        A=np.array([[np.searchsorted(es,np.datetime64(f'{d}T{h:02d}:{mi:02d}'))-np.searchsorted(xs,np.datetime64(f'{d}T{h:02d}:{mi:02d}')) for h,mi in slots] for d in ds])
        out['gates'][gate][k]=[int(v) for v in np.median(A,axis=0)]
    print(gate,{k:max(v) for k,v in out['gates'][gate].items()})
json.dump(out,open('checks/gate_profiles_2025.json','w'),ensure_ascii=False,separators=(',',':'))
