import numpy as np
from scipy.optimize import least_squares
HD,HB,HC,S=np.load('<SANDBOX_TMP>/m.npy')
def lev(Dq,B,C):
    w=np.linalg.eigvalsh(Dq*HD+B*HB+C*HC+1e6*S)
    w=w[w<1e5]; out=[]
    for x in w:
        if out and abs(x-out[-1][0])<1e-4: out[-1][1]+=1
        else: out.append([x,1])
    return out
L=lev(2000,500,2000); print([(round(x-L[0][0]),d) for x,d in L][:8])
obs=np.array([16700,26330,35020])
def res(p):
    Dq,B=p; L=lev(Dq,B,4*B); return [L[i][0]-L[0][0]-obs[i-1] for i in (1,2,3)]
for g in [(2000,500),(1800,400),(2500,600)]:
    r=least_squares(res,g); print(r.x,r.fun)
    print([(round(x-lev(*r.x,4*r.x[1])[0][0]),d) for x,d in lev(r.x[0],r.x[1],4*r.x[1])][:6])
