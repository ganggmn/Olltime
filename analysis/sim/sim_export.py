import json, os
o = json.load(open(os.path.expanduser('~/bt/sim_out.json'))); I = json.load(open(os.path.expanduser('~/bt/sim_in.json'))); S = json.load(open(os.path.expanduser('~/bt/sim_stat.json')))
TR = {e['d']: e for y in I for e in I[y]}
ev = []
for p in o['per']:
    c = o['charts'][p['d']]; e = TR[p['d']]
    def pack(a):
        ms = [m for m, _ in a]; assert all(ms[i + 1] - ms[i] == 20 for i in range(len(ms) - 1)), ms[:5]
        return [ms[0]] + [int(round(v / 10)) for _, v in a]
    ev.append(dict(d=p['d'], yr=p['yr'], st=p['st'], run=p['run'], name=p['name'], k=p['k'], truth=[int(round(v / 10)) for v in e['truth']], main=pack(c['main']), new=pack(c['new']),
                   acc=[round(p['main']['acc'], 1), round(p['new']['acc'], 1)], exit=e['exit']))
a24 = [x for x in ev if x['yr'] == '2024' and x['exit']]
json.dump(dict(made='2026-11-28', stats=S, ev=ev), open(os.path.expanduser('~/mnt/(주)한국체육산업개발 공모전/analysis/sim/sim_data.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print(len(ev), os.path.getsize(os.path.expanduser('~/mnt/(주)한국체육산업개발 공모전/analysis/sim/sim_data.json')))
for x in a24: print(x['d'], x['exit'])
