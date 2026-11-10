import ts, numpy as np
from scipy.optimize import least_squares
def spec(Dq,B):
    e=ts.levels(Dq,B)
    e=np.sort(e); g=e[0]
    # group distinct
    lv=[]; 
    for v in e:
        if lv and abs(v-lv[-1][0])<1e-3*max(1,abs(v))*0+1e-3: lv[-1][1]+=1
        else: lv.append([v,1])
    return [(round(v-g,1),m) for v,m in lv]
print(spec(1000,1000))
obs=np.array([10600,17500,27600.])
def res(p):
    Dq,B=p
    lv=spec(Dq,B)
    # levels after ground: T2 (mult3), T1 (mult3), T1 (mult3)
    ex=[l[0] for l in lv[1:4]]
    return np.array(ex)-obs
s=least_squares(res,[1000,900],x_scale=[1000,1000])
print(s.x, res(s.x), spec(*s.x))
