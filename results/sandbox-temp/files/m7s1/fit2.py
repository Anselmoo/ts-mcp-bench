import numpy as np
exec(open('fit.py').read().split('e,S=levels(0')[0])
def dbl(Dq,B):
    e,S=levels(Dq,B,4.4*B)
    d=np.sort(e[S==0.5]); 
    # group degenerate
    g=[d[0]]
    for x in d[1:]:
        if x-g[-1]>0.5 and all(abs(x-y)>0.5 for y in g): g.append(x)
    return S[0],np.array(sorted(set(np.round(d,1))))
obs=np.array([29360,29620,31640.])
from scipy.optimize import least_squares
def res(x):
    s,u=dbl(*x); return u[1:4]-obs
best=[]
for Dq in np.arange(2000,5001,100):
  for B in np.arange(100,1201,50):
    s,u=dbl(Dq,B)
    if s!=0.5: continue
    best.append((np.sum((u[1:4]-obs)**2),Dq,B))
best.sort(); print(best[:5])
for c0 in best[:3]:
    r=least_squares(res,[c0[1],c0[2]],diff_step=1e-3)
    print(r.x,r.fun,dbl(*r.x)[1][:6])
