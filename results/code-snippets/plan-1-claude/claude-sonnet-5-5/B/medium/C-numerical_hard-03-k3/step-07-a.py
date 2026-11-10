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
n=len(dets)
# precompute operator matrices linear in F2,F4 and Dq
def twoe(k):
  H=np.zeros((n,n))
  for a in ms:
   for b in ms:
    for c in ms:
     for d in ms:
      if a+b!=c+d: continue
      v=Ck[k,a,c]*Ck[k,d,b]
      if abs(v)<1e-12: continue
      for sa in (0,1):
       for sb in (0,1):
        oa,ob,oc,od=2*(a+2)+sa,2*(b+2)+sb,2*(c+2)+sa,2*(d+2)+sb
        if oa==ob: continue
        for d0 in dets:
          d1,s1=apply([(1,oa),(1,ob),(0,od),(0,oc)],d0)
          if d1 is None: continue
          H[idx[d1],idx[d0]]+=0.5*v*s1
  return H
H2,H4=twoe(2),twoe(4)
h=np.zeros((5,5))
for (a,b),v in {(0,0):1,(2,2):.5,(-2,-2):.5,(2,-2):.5,(-2,2):.5}.items(): h[a+2,b+2]=v
HL=np.zeros((n,n))
for a in ms:
 for b in ms:
  if h[a+2,b+2]==0: continue
  for s in (0,1):
   for d0 in dets:
    d1,s1=apply([(1,2*(a+2)+s),(0,2*(b+2)+s)],d0)
    if d1 is None: continue
    HL[idx[d1],idx[d0]]+=h[a+2,b+2]*s1
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
w,v=np.linalg.eigh((M+M.T)/2)
Dm=v[:,np.abs(w-0.75)<1e-6]
A2,A4,AL=[Dm.T@((X+X.T)/2)@Dm for X in (H2,H4,HL)]
def levels(B,Cc,Dq):
  e=np.linalg.eigvalsh((49*B+7*Cc)*A2+(63*Cc/5)*A4+10*Dq*AL); return e-e[0]
def clus(e):
  out=[]
  for x in e:
    if not out or x-out[-1]>1: out.append(x)
  return np.array(out)
obs=np.array([22640,22930,25080])
def res(p):
  return clus(levels(p[0],4.6*p[0],p[1]))[1:4]-obs
best=[]
for B in np.arange(200,1000,50):
  for Dq in np.arange(2000,4500,100):
    r=least_squares(res,(B,Dq))
    best.append((np.sum(r.fun**2),tuple(np.round(r.x,1))))
best.sort(); print(best[:8])
b=best[0][1]; print(clus(levels(b[0],4.6*b[0],b[1]))[:8])
