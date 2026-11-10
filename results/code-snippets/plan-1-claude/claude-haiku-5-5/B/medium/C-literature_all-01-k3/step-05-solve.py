import numpy as np
from ni import energies
from scipy.optimize import fsolve
def levels(Dq,B):
    H,_=energies(Dq,B,4.5*B)
    ev=np.sort(np.linalg.eigvalsh(H))
    # group
    out=[];cur=[ev[0]]
    for e in ev[1:]:
        if abs(e-cur[-1])<1e-6: cur.append(e)
        else: out.append((np.mean(cur),len(cur))); cur=[e]
    out.append((np.mean(cur),len(cur)))
    return out
def resid(p):
    Dq,B=p
    L=levels(Dq,B); g=L[0][0]
    # levels: 3T1F(3), 3T2(3), 3A2(1), 3T1P(3)
    print(Dq,B,[(round(e-g,1),m) for e,m in L]) if False else None
    t1=[e-g for e,m in L if m==3]
    return [t1[1]-4400, t1[2]-15500]
for Dq,B in [(440,800),(500,700)]:
    print([(round(e-levels(Dq,B)[0][0],1),m) for e,m in levels(Dq,B)])
sol=fsolve(resid,[440,800],xtol=1e-10)
print("solution Dq,B:",sol, "C=",4.5*sol[1])
print([(round(e-levels(*sol)[0][0],1),m) for e,m in levels(*sol)])
