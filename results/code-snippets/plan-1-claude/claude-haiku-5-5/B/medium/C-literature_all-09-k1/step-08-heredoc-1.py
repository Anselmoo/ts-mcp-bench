import numpy as np
from scipy.optimize import least_squares
d=np.load('<SANDBOX_TMP>/ops.npz'); H1,M2,M4=d['H1'],d['M2'],d['M4']
def levels(p):
    Dq,B,C=p
    F2=49*B+7*C; F4=441*C/35
    ev=np.linalg.eigvalsh(Dq*H1+F2*M2+F4*M4)
    return ev
def distinct(ev,tol=1e-3):
    out=[]
    for e in ev:
        if not out or abs(e-out[-1][0])>tol: out.append([e,1])
        else: out[-1][1]+=1
    return out
p=[800,800,3500]
ev=levels(p); dl=distinct(ev-ev[0]); print([(round(a,1),b) for a,b in dl])
obs=np.array([19720,23260,24980.])
def res(p):
    ev=levels(p); d=distinct(ev-ev[0])
    # take lowest three distinct excited levels (quartets)
    return d[1:4] and np.array([d[1][0],d[2][0],d[3][0]])-obs
# scan a grid over Dq and find solution
best=None
for Dq in np.linspace(500,1200,15):
  for B in np.linspace(500,1200,15):
    for C in np.linspace(2500,5000,11):
        r=res([Dq,B,C]); c=np.sum(r**2)
        if best is None or c<best[0]: best=(c,[Dq,B,C])
print("grid best",best)
sol=least_squares(res,best[1],xtol=1e-12,ftol=1e-12,gtol=1e-12)
print("solution Dq,B,C:",sol.x, "resid",res(sol.x))
ev=levels(sol.x); print([(round(a,1),b) for a,b in distinct(ev-ev[0])][:6])
