import numpy as np
from scipy.optimize import least_squares
H2,H4,HV=np.load('m.npy')
def levels(Dq,B,Cc):
    F4=Cc/35*441/441*441/441; F4=Cc*441/35/441  # F4 (Condon-Shortley scaled) : C=35F4 with F4=F^4/441
    # B=F2-5F4, C=35F4 with F2=F^2/49,F4=F^4/441
    f4=Cc/35; f2=B+5*f4
    H=f2*49*H2+f4*441*H4+Dq*HV
    e=np.linalg.eigvalsh(H); e=np.round(e-e[0],3)
    u,c=np.unique(e,return_counts=True); return list(zip(u,c))
print(levels(0,1000,4000)[:6])
print(levels(800,800,3200)[:8])
def res(x):
    L=levels(*x); q=[u for u,c in L[1:]]
    return np.array(q[:3])-[19720,23260,24980]
s=least_squares(res,[800,800,3200]); print(s.x, res(s.x)); print(levels(*s.x)[:6])
