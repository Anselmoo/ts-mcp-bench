import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
Ck={}
for k in (2,4):
  for a in ms:
    for b in ms:
      q=a-b
      Ck[k,a,b]=float((-1)**a*gaunt(2,k,2,-a,q,b)*np.sqrt(4*np.pi/(2*k+1))) if abs(q)<=k else 0.0
orbs=[(m,s) for m in ms for s in (0,1)]
dets=[d for d in itertools.combinations(range(10),5) if sum(orbs[i][1]==0 for i in d)==3]
idx={d:i for i,d in enumerate(dets)}
def apply(ops,d):
  d=list(d);sign=1
  for cr,o in reversed(ops):
    if cr:
      if o in d: return None,0
      pos=sum(1 for x in d if x<o); d.insert(pos,o)
    else:
      if o not in d: return None,0
      pos=d.index(o); d.pop(pos)
    sign*=(-1)**pos
  return tuple(d),sign
def g(F,a,b,c,d):
  if a+b!=c+d: return 0
  return sum(F[k]*Ck[k,a,c]*Ck[k,d,b] for k in (2,4))
n=len(dets)
def build(B,Cc,Dq):
  F={2:49*B+7*Cc,4:63*Cc/5}
  H=np.zeros((n,n))
  for a in ms:
   for b in ms:
    for c in ms:
     for d in ms:
      v=g(F,a,b,c,d)
      if abs(v)<1e-12: continue
      for sa in (0,1):
       for sb in (0,1):
        oa,ob,oc,od=2*(a+2)+sa,2*(b+2)+sb,2*(c+2)+sa,2*(d+2)+sb
        if oa==ob: continue
        for d0 in dets:
          d1,s1=apply([(1,oa),(1,ob),(0,od),(0,oc)],d0)
          if d1 is None: continue
          H[idx[d1],idx[d0]]+=0.5*v*s1
  h=np.zeros((5,5))
  P={(0,0):1,(2,2):.5,(-2,-2):.5,(2,-2):.5,(-2,2):.5}
  for (a,b),v in P.items(): h[a+2,b+2]=v*10*Dq
  for a in ms:
   for b in ms:
    if h[a+2,b+2]==0: continue
    for s in (0,1):
      for d0 in dets:
        d1,s1=apply([(1,2*(a+2)+s),(0,2*(b+2)+s)],d0)
        if d1 is None: continue
        H[idx[d1],idx[d0]]+=h[a+2,b+2]*s1
  return H
M=np.zeros((n,n))
for d0 in dets:
  j=idx[d0]; M[j,j]+=0.75
  for m in ms:
    for m2 in ms:
      d1,s1=apply([(1,2*(m+2)+0),(0,2*(m+2)+1)],d0)
      if d1 is None: continue
      d2,s2=apply([(1,2*(m2+2)+1),(0,2*(m2+2)+0)],d1)
      if d2 is None: continue
      M[idx[d2],j]+=s1*s2
Ms=(M+M.T)/2
print(sorted(set(np.round(np.linalg.eigvalsh(Ms),3))))
w,v=np.linalg.eigh(Ms)
Dm=v[:,np.abs(w-0.75)<1e-6]
def levels(B,Cc,Dq):
  H=build(B,Cc,Dq); H=(H+H.T)/2
  return np.linalg.eigvalsh(Dm.T@H@Dm)
e=levels(500,2300,3000); print(np.round(e-e[0],0))
obs=np.array([22640,22930,25080])
def res(p):
  B,Dq=p
  e=levels(B,4.6*B,Dq); u=np.unique(np.round(e-e[0],2))
  return u[1:4]-obs
for g0 in [(500,3000),(600,3500),(400,2800),(700,3000),(500,2500),(450,3300)]:
  r=least_squares(res,g0); print(g0,r.x,r.fun)
