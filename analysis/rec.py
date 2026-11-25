import pandas as pd,numpy as np
p=pd.read_csv('parking/parking.csv',encoding='utf-8-sig');p['t']=pd.to_datetime(p.collected_at)
a=p[p.t.dt.date.astype(str)=='2026-11-23'].copy();b=p[p.t.dt.date.astype(str)=='2026-11-24'].copy()
a['m']=a.t.dt.hour*60+a.t.dt.minute;b['m']=b.t.dt.hour*60+b.t.dt.minute
model=np.interp(b.m.values,a.m.values,a.parking_sum.values);v=b.parking_sum.values.astype(float)
print('오늘(11/24) 자료',len(b),'건,',b.t.iloc[0].strftime('%H:%M'),'~',b.t.iloc[-1].strftime('%H:%M'))
for w in (200,300,400):
    lo=np.floor(v/w)*w;hi=lo+w;mid=(lo+hi)/2
    est=np.empty(len(v));ratio=1.0;off=0.0
    for i in range(len(v)):
        if i>0 and lo[i]!=lo[i-1] and abs(lo[i]-lo[i-1])<=w*1.5:
            anchor=lo[i] if lo[i]>lo[i-1] else hi[i]      # 범위를 넘는 순간 = 그 경계값이 실제 값
            off=anchor-model[i]                              # 어제 모양과의 차이를 그 순간에 다시 맞춤
        est[i]=np.clip(model[i]+off,lo[i],hi[i])
    clip_only=np.clip(model,lo,hi)
    day=(b.m.values>=360)
    f=lambda x:np.abs(x-v)[day].mean();g=lambda x:np.abs(np.diff(x)-np.diff(v))[day[1:]].mean()
    print(f'폭 {w}: 수준 오차  가운데값 {f(mid):.0f} | 어제 모양을 범위에 끼움 {f(clip_only):.0f} | +넘는 순간마다 다시 맞춤 {f(est):.0f}   ||  10분 변화 오차  {g(mid):.0f} | {g(clip_only):.0f} | {g(est):.0f}')
print('어제 모양 그대로(범위 안 봄) 오차',f"{np.abs(model-v)[b.m.values>=360].mean():.0f}")
