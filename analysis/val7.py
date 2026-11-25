import os,pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
src=open(os.path.expanduser('~/val6.py')).read();src=src[:src.index("for TG,lab in")]
exec(src)
lp=pd.read_csv('livingpop_songpa_2024_2025.csv',dtype={'date':str,'dong':str});lp['total']=pd.to_numeric(lp.total,errors='coerce')
lp['ts']=pd.to_datetime(lp.date)+pd.to_timedelta(lp.hour.astype(int),unit='h')
P=lp.pivot_table(index='ts',columns='dong',values='total')
big=set(D[D.aud>=1.2].date.unique());none=set(D[D.aud==0].date.unique())
ev=P[(P.index.hour==19)&(P.index.year==2025)];dstr=ev.index.strftime('%Y-%m-%d')
up=(ev[dstr.isin(big)].mean()/ev[dstr.isin(none)].mean()).sort_values(ascending=False)
print('공연 날 19시 생활인구 ÷ 공연 없는 날 (동별 상위)');print(up.head(5).round(2).to_string());print('동 수',P.shape[1])
dong=up.index[0];s=P[dong];print('선택한 동',dong,'평소 19시',round(ev[dstr.isin(none)][dong].mean()),'큰 공연 날 19시',round(ev[dstr.isin(big)][dong].mean()))
D['lp']=s.reindex(D.index).values;D['lp7']=s.reindex(D.index-pd.Timedelta('7D')).values
ok=D.lp.notna()&(D.h>=7);print('주차장 안 차량과 생활인구 상관(같은 시각)',round(np.corrcoef(D.O[ok],D.lp[ok])[0,1],3),'| 생활인구 있는 날',D[ok].date.nunique(),'/',D.date.nunique())
typ=D.groupby(['dt0','h']).lp.transform('mean');a0=(D.lp/typ-1).fillna(0).values;a7=(D.lp7/typ-1).fillna(0).values
SF0=SF.copy();pt=D.part.values;wk=(D.dt0.values>=5)
def F(a): return np.hstack([a[:,None]*oh(pt,3),(a*wk)[:,None]*oh(pt,3),a[:,None]*oh(D.h.values//2,12)])
import builtins
for TG,lab in (('O','주차장 안 차량'),('E','시간당 입차'),('X','시간당 출차')):
    print('\n'+lab,'| 전체, 1..12월 | 명절')
    globals()['SF']=SF0;print(' 지금 최선                 ',*run(TG,'dt1',0))
    globals()['SF']=np.hstack([SF0,F(a7)]);print(' +지난주 생활인구(예측용)  ',*run(TG,'dt1',0))
    globals()['SF']=np.hstack([SF0,F(a0)]);print(' +같은 시각 생활인구(복원용)',*run(TG,'dt1',0))
# 2024 명절·연휴: 생활인구로 본 변화
s24=P[dong];day=s24[(s24.index.hour>=10)&(s24.index.hour<=20)].groupby(s24[(s24.index.hour>=10)&(s24.index.hour<=20)].index.date).mean()
import datetime as dt
def rel(d):
    d=dt.date.fromisoformat(d);v=[day.get(d+dt.timedelta(7*k)) for k in (-3,-2,-1,1,2,3)];v=[x for x in v if x is not None and not np.isnan(x)]
    return round((day[d]/np.mean(v)-1)*100) if d in day.index and v else None
print('\n낮 생활인구, 앞뒤 3주 같은 요일 대비 %')
for n,ds in {'2024 설(2/9~12)':['2024-02-09','2024-02-10','2024-02-11','2024-02-12'],'2024 추석(9/16~18)':['2024-09-16','2024-09-17','2024-09-18'],'2025 설':['2025-01-28','2025-01-29','2025-01-30'],'2025 추석':['2025-10-05','2025-10-06','2025-10-07'],
 '2024 평일 낀 연휴(3/1금,5/6월,6/6목,8/15목,10/1화,10/3목,10/9수)':['2024-03-01','2024-05-06','2024-06-06','2024-08-15','2024-10-01','2024-10-03','2024-10-09'],
 '2025 평일 낀 연휴(3/3,5/5,5/6,6/6,8/15,10/9)':['2025-03-03','2025-05-05','2025-05-06','2025-06-06','2025-08-15','2025-10-09']}.items():
    print(' ',n,[rel(d) for d in ds])
