cat << 'EOF' | python3 -
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
Vk={k:np.zeros((n,n,n,n)) for k in (2,4)}
for i in range(n):
 for j in range(n):
  for a in range(n):
   for b in range(n):
    for k in (2,4):
      v=V2(k,so[i],so[j],so[a],so[b])
      if abs(v)>1e-14: Vk[k][i,j,a,b]=v
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
HF={}
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
  HF[k]=H
for B,Cc in [(1,0),(1,3),(1,4.5)]:
  H=HF[2]*(49*B+7*Cc)+HF[4]*12.6*Cc
  ev=np.round(np.linalg.eigvalsh(H),4); print(B,Cc,np.unique(ev))
EOF