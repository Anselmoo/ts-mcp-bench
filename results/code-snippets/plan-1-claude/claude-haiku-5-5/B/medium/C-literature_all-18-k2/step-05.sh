cat << 'EOF' | python3 -
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
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
      h1[so.index((m,s)),so.index((mp,s))]=21*Moct[a,b]   # per unit Dq
ups=[i for i,o in enumerate(so) if o[1]==1]
dns=[i for i,o in enumerate(so) if o[1]==-1]
basis=[tuple(sorted(ups+list(dn))) for dn in itertools.combinations(dns,3)]
D=len(basis); bidx={b:i for i,b in enumerate(basis)}
def op_apply(occ,i,j,k,l):
    # c†_i c†_j c_l c_k
    s=list(occ); sign=1
    for x in (k,l):
        if x not in s: return None
        p=s.index(x); sign*=(-1)**p; s.pop(p)
    for x in (j,i):
        if x in s: return None
        p=sum(1 for y in s if y<x); sign*=(-1)**p; s.insert(p,x)
    return sign,tuple(s)
def opmat(fun):
    H=np.zeros((D,D))
    for c,occ in enumerate(basis):
        for (coef,i,j,k,l) in fun:
            r=op_apply(occ,i,j,k,l)
            if r and r[1] in bidx:
                H[bidx[r[1]],c]+=coef*r[0]
    return H
def ee_terms(F):
    # returns list of (coef, i,j,k,l) for 1/2 sum V c†i c†j c_l c_k
    terms=[]
    for i in range(n):
     for j in range(n):
      for a in range(n):
       for b in range(n):
        v=sum(F[k]*Vk[k][i,j,a,b] for k in (0,2,4))
        if abs(v)>1e-14: terms.append((0.5*v,i,j,b,a))  # c_l c_k with l=b (second), k=a
    return terms
def cf_terms(h):
    t=[]
    for i in range(n):
      for j in range(n):
        if abs(h[i,j])>1e-14: t.append((h[i,j],i,j,j,i)) # placeholder not used
    return t
# one-electron operator: sum h_ab c†_a c_b -> use opmat with direct
def onebody(h):
    H=np.zeros((D,D))
    for c,occ in enumerate(basis):
        for a in range(n):
            for b in range(n):
                if abs(h[a,b])<1e-14: continue
                s=list(occ)
                if b not in s: continue
                p=s.index(b); sg=(-1)**p; s.pop(p)
                if a in s: continue
                q=sum(1 for y in s if y<a); sg*=(-1)**q; s.insert(q,a)
                t=tuple(s)
                if t in bidx: H[bidx[t],c]+=h[a,b]*sg
    return H
def energies(Dq,B,C_):
    F={0:0.0,2:49*B+7*C_,4:12.6*C_}
    Hee=opmat(ee_terms(F))
    Hcf=onebody(h1*Dq)
    return np.linalg.eigvalsh(Hee+Hcf), Hee
# check free ion: Dq=0
B=1.0; Cc=4.5
ev,Hee=energies(0,B,Cc)
print(np.round(np.unique(np.round(ev,6)),6))
EOF