import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import sqrt, pi
l=2
ms=[-2,-1,0,1,2]
so=[(m,s) for s in (1,-1) for m in ms]
n=len(so)
def C(k,q,m,mp):
    if m-mp!=q: return 0.0
    return sqrt(4*pi/(2*k+1))*(-1)**m*float(gaunt(l,k,l,-m,q,mp))
def V2(k,i,j,kk,ll):
    mi,si=i; mj,sj=j; mk,sk=kk; mll,sl=ll
    if si!=sk or sj!=sl: return 0.0
    return sum((-1)**q*C(k,q,mi,mk)*C(k,-q,mj,mll) for q in range(-k,k+1))
Vk={k:np.zeros((n,n,n,n)) for k in (0,2,4)}
for i in range(n):
 for j in range(n):
  for a in range(n):
   for b in range(n):
    for k in (0,2,4):
      v=V2(k,so[i],so[j],so[a],so[b])
      if abs(v)>1e-14: Vk[k][i,j,a,b]=v
M=lambda q: np.array([[C(4,q,m,mp) for mp in ms] for m in ms])
Moct=M(0)+sqrt(5/14)*(M(4)+M(-4))
h1=np.zeros((n,n))
for s in (1,-1):
  for a,m in enumerate(ms):
    for b,mp in enumerate(ms):
      h1[so.index((m,s)),so.index((mp,s))]=21*Moct[a,b]
ups=[i for i,o in enumerate(so) if o[1]==1]
dns=[i for i,o in enumerate(so) if o[1]==-1]
basis=[tuple(sorted(ups+list(dn))) for dn in itertools.combinations(dns,3)]
D=len(basis); bidx={b:i for i,b in enumerate(basis)}
def apply2(occ,i,j,k,l):
    s=list(occ); sign=1
    for x in (k,l):
        if x not in s: return None
        p=s.index(x); sign*=(-1)**p; s.pop(p)
    for x in (j,i):
        if x in s: return None
        p=sum(1 for y in s if y<x); sign*=(-1)**p; s.insert(p,x)
    return sign,tuple(s)
def applyop(occ,a,b):
    s=list(occ)
    if b not in s: return None
    p=s.index(b); sg=(-1)**p; s.pop(p)
    if a in s: return None
    q=sum(1 for y in s if y<a); sg*=(-1)**q; s.insert(q,a)
    return sg,tuple(s)
Hcf=np.zeros((D,D))
for c,occ in enumerate(basis):
    for a in range(n):
        for b in range(n):
            if abs(h1[a,b])<1e-14: continue
            r=applyop(occ,a,b)
            if r and r[1] in bidx: Hcf[bidx[r[1]],c]+=h1[a,b]*r[0]
print("Hcf sym", np.allclose(Hcf,Hcf.T))
print("Hcf eig", np.round(np.linalg.eigvalsh(Hcf),4))
print("Hcf offdiag nonzero count", np.sum(np.abs(Hcf-np.diag(np.diag(Hcf)))>1e-9))
for k in (2,4):
  H=np.zeros((D,D))
  for c,occ in enumerate(basis):
    for i in range(n):
     for j in range(n):
      for a in range(n):
       for b in range(n):
        v=Vk[k][i,j,a,b]
        if abs(v)<1e-14: continue
        r=apply2(occ,i,j,b,a)
        if r and r[1] in bidx: H[bidx[r[1]],c]+=0.5*v*r[0]
  print("k",k,"sym",np.allclose(H,H.T), np.round(np.linalg.eigvalsh(H),4))
