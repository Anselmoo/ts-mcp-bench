import ts, numpy as np
from scipy.optimize import brentq
def spec(Dq,B):
    e=np.sort(ts.levels(Dq,B)); g=e[0]
    lv=[]
    for v in e:
        if lv and abs(v-lv[-1][0])<1e-3: lv[-1][1]+=1
        else: lv.append([v,1])
    return [v-g for v,m in lv]
for B in [800,900,1000,1100]:
    print(B, [round(x) for x in spec(1060,B)])
