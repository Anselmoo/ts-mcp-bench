cat << 'EOF' | python3 -
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import sqrt, pi
from scipy.optimize import least_squares
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
def apply_ops(occ, ops):
    s=list(occ); sign=1
    for typ,x in reversed(ops):
        if typ=='a':
            if x not in s: return None
            p=s.index(x); sign*=(-1)**p; s.pop(p)
        else:
            if x in s: return None
            p=sum(1 for y in s if y<x); sign*=(-1)**p; s.insert(p,x)
    return sign,tuple(s)
def build_two(k):
  H=np.zeros((D,D))
  for c,occ in enumerate(basis):
    for i in range(n):
     for j in range(n):
      for a in range(n):
       for b in range(n):
        v=Vk[k][i,j,a,b]
        if abs(v)<1e-14: continue
        r=apply_ops(occ,[('c',i),('c',j),('a',b),('a',a)])
        if r and r[1] in bidx: H[bidx[r[1]],c]+=0.5*v*r[0]
  return H
HF={k:build_two(k) for k in (2,4)}
Hcf=np.zeros((D,D))
for c,occ in enumerate(basis):
    for a in range(n):
        for b in range(n):
            if abs(h1[a,b])<1e-14: continue
            r=apply_ops(occ,[('c',a),('a',b)])
            if r and r[1] in bidx: Hcf[bidx[r[1]],c]+=h1[a,b]*r[0]
def levels(Dq,B,Cc=None):
    if Cc is None: Cc=4.5*B
    H=Dq*Hcf+HF[2]*(49*B+7*Cc)+HF[4]*12.6*Cc
    ev=np.linalg.eigvalsh(H)
    return ev
def bands(p):
    Dq,B=p
    ev=levels(Dq,B)
    g0=ev[0]
    t2=ev[1]; t1a=ev[4]; t1b=ev[7]
    return np.array([t2-g0, t1a-g0, t1b-g0])
obs=np.array([10600,17500,27600.])
sol=least_squares(lambda p: bands(p)-obs,[1000,900],x_scale=[1000,500])
print("Dq,B =",sol.x,"C=",4.5*sol.x[1])
print("calc bands",bands(sol.x),"obs",obs)
# also with 2-band fits
for pair in [(0,1),(0,2),(1,2)]:
    s2=least_squares(lambda p: (bands(p)-obs)[list(pair)],[1000,900],x_scale=[1000,500])
    print(pair, s2.x, bands(s2.x))
EOF