import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import sqrt,pi,N
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
c={}
for k in (2,4):
  for a in ms:
    for b in ms:
      q=a-b
      if abs(q)>k: c[k,a,b]=0.0;continue
      # ∫Y*_a Y_kq Y_b = (-1)^a ∫ Y_-a Y_kq Y_b
      c[k,a,b]=float(N((-1)**a*gaunt(2,k,2,-a,q,b)*sqrt(4*pi/(2*k+1))))
# real orbitals in m basis: columns
s=1/np.sqrt(2)
def vec(d):
  v=np.zeros(5,complex)
  for m,x in d.items(): v[m+2]=x
  return v
dz2=vec({0:1}); dx2=vec({2:s,-2:s}); dxy=vec({2:-1j*s,-2:1j*s})
dxz=vec({1:s,-1:-s}); dyz=vec({1:1j*s,-1:1j*s})
def spectrum(Dq,B,C,nu,nd):
  F2=(49*B+7*C)/49; F4=(63*C/5)/441
  F={2:F2,4:F4,0:0}
  # h in m basis
  h=np.zeros((5,5),complex)
  for v in (dz2,dx2): h+=6*Dq*np.outer(v,v.conj())
  for v in (dxy,dxz,dyz): h+=-4*Dq*np.outer(v,v.conj())
  # two-electron (m basis) g[a,b,c,d]=<ab|cd>
  g=np.zeros((5,5,5,5))
  for a in range(5):
   for b in range(5):
    for cc in range(5):
     for d in range(5):
      if a+b!=cc+d: continue
      g[a,b,cc,d]=sum(F[k]*c[k,a-2,cc-2]*c[k,d-2,b-2] for k in (2,4))
  # spin orbitals idx = 2*m+spin
  n=10
  dets=[]
  for up in itertools.combinations(range(5),nu):
    for dn in itertools.combinations(range(5),nd):
      dets.append(tuple(sorted([2*i for i in up]+[2*i+1 for i in dn])))
  idx={d:i for i,d in enumerate(dets)}
  H=np.zeros((len(dets),len(dets)),complex)
  def ann(d,i):
    if i not in d: return None
    p=d.index(i); return tuple(x for x in d if x!=i),(-1)**p
  def cre(d,i):
    if i in d: return None
    l=list(d); p=sum(1 for x in l if x<i); l.insert(p,i); return tuple(l),(-1)**p
  for d in dets:
    j=idx[d]
    for i in range(n):
      for k in range(n):
        if i%2!=k%2: continue
        hv=h[i//2,k//2]
        if hv==0: continue
        r=ann(d,k)
        if r is None: continue
        r2=cre(r[0],i)
        if r2 is None: continue
        H[idx[r2[0]],j]+=hv*r[1]*r2[1]
    for i in range(n):
     for jj in range(n):
      for k in range(n):
       for l in range(n):
        if i%2!=k%2 or jj%2!=l%2: continue
        gv=g[i//2,jj//2,k//2,l//2]
        if gv==0: continue
        r=ann(d,l)
        if r is None: continue
        r2=ann(r[0],k)
        if r2 is None: continue
        r3=cre(r2[0],jj)
        if r3 is None: continue
        r4=cre(r3[0],i)
        if r4 is None: continue
        H[idx[r4[0]],j]+=0.5*gv*r[1]*r2[1]*r3[1]*r4[1]
  return np.linalg.eigvalsh(H)
def singlets(Dq,B,C):
  e0=spectrum(Dq,B,C,3,3); e1=spectrum(Dq,B,C,4,2)
  e0=list(e0)
  for x in e1:
    i=int(np.argmin([abs(x-y) for y in e0])); e0.pop(i)
  e0=np.array(sorted(e0)); return e0-e0[0]
def levels(e,n=3):
  out=[];
  for x in e[1:]:
    if not out or x-out[-1][0]>1: out.append([x,1])
    else: out[-1][1]+=1
  return out[:n]
if __name__=="__main__":
  print(levels(singlets(2000,600,2700),5))
