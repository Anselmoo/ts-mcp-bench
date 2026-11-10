cd <SANDBOX_TMP> && python3 -c "
from a import *
from scipy.optimize import fsolve
def f(p):
    Dq,B,C=p
    t=table(B,C,Dq)
    q=[x for x in t if x[3]>3]; d=[x for x in t if x[3]<1 and x[1]==3 and x[2]==1]
    return q,d
def r(p):
    q,d=f(p)
    return [q[1][0]-8100,q[3][0]-19400,d[1][0]-21600]
for x0 in [(900,800,3000),(950,850,3500),(1000,900,3000)]:
    s=fsolve(r,x0,epsfcn=1e-3);print(s,r(s)); q,d=f(s);print(q,d)
"