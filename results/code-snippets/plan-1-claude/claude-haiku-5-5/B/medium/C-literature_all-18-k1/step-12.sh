python3 - << 'EOF' 2>/dev/null | grep -v -E "unit|scaled"
import ts, numpy as np
from scipy.optimize import fsolve
def spec(Dq,B):
    e=np.sort(ts.levels(Dq,B)); g=e[0]
    lv=[]
    for v in e:
        if lv and abs(v-lv[-1][0])<1e-3: lv[-1][1]+=1
        else: lv.append([v,1])
    return [v-g for v,m in lv]
def f(p):
    s=spec(*p); return [s[1]-10600, s[2]-17500]
for guess in [(1000,900),(1060,1000),(1100,1100)]:
    sol=fsolve(f,guess); print("fit nu1,nu2:",sol, [round(x) for x in spec(*sol)])
def g(p):
    s=spec(*p); return [s[2]-17500, s[3]-27600]
for guess in [(1000,900),(1060,1000),(1100,1100)]:
    sol=fsolve(g,guess); print("fit nu2,nu3:",sol, [round(x) for x in spec(*sol)])
EOF