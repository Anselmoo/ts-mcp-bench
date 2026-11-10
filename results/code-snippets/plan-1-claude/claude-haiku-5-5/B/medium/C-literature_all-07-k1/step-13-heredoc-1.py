import numpy as np
from scipy.optimize import fsolve
d=np.load('<SANDBOX_TMP>/ops.npz')
Ho,O2,O4,S2=d['Ho'],d['O2'],d['O4'],d['S2']
def H(Dq,B,C):
    return Dq*Ho+(49*B+7*C)*O2+12.6*C*O4
def clusters(Dq,B,C):
    w,v=np.linalg.eigh(H(Dq,B,C))
    s=np.einsum('ia,ij,ja->a',v,S2,v)
    e6=w[abs(s-8.75)<1e-6].min()
    q=np.sort(w[abs(s-3.75)<1e-6])-e6
    out=[]
    for e in q:
        if not out or abs(e-out[-1][0])>1e-4: out.append([e,1])
        else: out[-1][1]+=1
    return out
def resid(p, targ=(19240,21890,23000)):
    Dq,B,C=p
    cl=clusters(Dq,B,C)
    return [cl[i][0]-targ[i] for i in range(3)]
for g in [(1000,800,3200),(1200,600,2500),(800,900,4000)]:
    sol,info,ier,msg=fsolve(resid,g,full_output=True)
    print("guess",g,"->",np.round(sol,2),ier, np.round(resid(sol),4))
    print("  clusters (E, deg):",[(round(e,1),n) for e,n in clusters(*sol)[:5]])
