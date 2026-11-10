import numpy as np
from scipy.optimize import least_squares
z=np.load('m.npz');HD,F2,F4,S2=z['HD'],z['F2'],z['F4'],z['S2']
def levels(Dq,B,C):
    H=Dq*HD+(49*B+7*C)*F2+(441*C/35)*F4
    w,v=np.linalg.eigh(H+1e-4*S2)
    s=np.einsum('ji,jk,ki->i',v,S2,v)
    S=np.round(-1+np.sqrt(1+4*s))/2
    return w-w[0],S
e,S=levels(0,1000,4000)
print(sorted(set(zip(np.round(e,0),S)))[:5])
def dbl(Dq,B,C=None):
    e,S=levels(Dq,B,4.4*B if C is None else C)
    vals=np.round(e[S==0.5],2); u=np.unique(vals); return S[0],u
print(dbl(3000,600))
obs=np.array([29360,29620,31640.])
def res(x):
    s,u=dbl(*x); return u[1:4]-obs
best=None
for Dq0 in [2500,3000,3500,4000]:
  for B0 in [300,500,700,900]:
    r=least_squares(res,[Dq0,B0])
    if best is None or r.cost<best.cost: best=r
    print(Dq0,B0,r.x,r.fun, dbl(*r.x)[0])
print(best.x,best.fun,dbl(*best.x)[1][:8])
