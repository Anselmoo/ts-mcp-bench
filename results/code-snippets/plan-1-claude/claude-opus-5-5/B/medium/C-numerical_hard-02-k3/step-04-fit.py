import numpy as np
from scipy.optimize import least_squares
MC,M2,M4,S2=np.load('mats.npy')
def trip(Dq,B,C):
    F2=49*(B+C/7); F4=441*C/35
    w,v=np.linalg.eigh(Dq*MC+F2*M2+F4*M4)
    s=np.einsum('ji,jk,ki->i',v,S2,v); S=np.round((-1+np.sqrt(1+4*s))/2)
    # group levels
    lv=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and w[j]-w[i]<1e-3: j+=1
        lv.append((w[i],j-i,S[i])); i=j
    return lv
for Dq in [2000,2500,3000]:
  lv=trip(Dq,700,3010); g=lv[0]
  print(Dq,[(round(e-g[0]),d,s) for e,d,s in lv[:14]])
obs=np.array([22900,23730,24580])
def res(p):
    Dq,B=p; lv=trip(Dq,B,4.3*B)
    assert lv[0][2]==1
    t=[e-lv[0][0] for e,d,s in lv[1:] if s==1][:3]
    return np.array(t)-obs
best=None
for Dq0 in np.arange(1500,4001,250):
  for B0 in np.arange(300,1201,100):
    try:
      r=least_squares(res,[Dq0,B0])
    except AssertionError: continue
    if best is None or r.cost<best.cost: best=r
    if r.cost<1: print(r.x, r.fun)
print(best.x,best.fun)
lv=trip(*best.x,4.3*best.x[1]); print([(round(e-lv[0][0]),d,s) for e,d,s in lv[:15]])
