import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
from math import sqrt, pi
l=2
ms=[-2,-1,0,1,2]
so=[(m,s) for s in (1,-1) for m in ms]
def C(k,q,m,mp):
    # <l m|C^k_q|l mp> = sqrt(4pi/(2k+1)) * int Y*_{lm} Y_{kq} Y_{l mp}
    if abs(q)>k or abs(m)>l or abs(mp)>l or m!=mp+q: 
        if m-mp!=q: return 0.0
    return sqrt(4*pi/(2*k+1))*(-1)**m*float(gaunt(l,k,l,-m,q,mp))
def V2(k,i,j,kk,ll):
    # <ij|C^k(1).C^k(2)|kk ll> with spin orbitals i=(m,s)
    mi,si=i; mj,sj=j; mk,sk=kk; mll,sl=ll
    if si!=sk or sj!=sl: return 0.0
    tot=0.0
    for q in range(-k,k+1):
        tot+= (-1)**q * C(k,q,mi,mk)*C(k,-q,mj,mll)
    return tot
def Hee(F):
    # F = {0:F0,2:F2,4:F4}
    n=len(so)
    H=np.zeros((n,n))
    return H
# build determinant basis: 8 electrons, Ms=1 => 5 up, 3 down
ups=[i for i,o in enumerate(so) if o[1]==1]
dns=[i for i,o in enumerate(so) if o[1]==-1]
basis=[]
for dn in itertools.combinations(dns,3):
    occ=tuple(sorted(ups+list(dn)))
    basis.append(occ)
D=len(basis)
def apply_ops(terms, occ):
    # terms: list of (coef, creators list, annihilators list) applied as c†_a c†_b c_c c_d ; here generic
    pass
def op2(occ,i,j,k,l):
    # c†_i c†_j c_l c_k acting on determinant occ (sorted tuple); return (sign, newocc) or None
    s=list(occ)
    sign=1
    # annihilate k then l
    for x in (k,l):
        if x not in s: return None
        p=s.index(x); sign*= (-1)**p; s.pop(p)
    # create j then i (c†_i c†_j)
    for x in (j,i):
        if x in s: return None
        # insert at sorted position
        p=sum(1 for y in s if y<x)
        sign*=(-1)**p; s.insert(p,x)
    return sign,tuple(s)
def build(F0,F2,F4,Dq_unit, B_C=None):
    pass
# precompute two-electron integrals in spin-orbital basis
n=len(so)
Rk={0:1.0,2:1.0,4:1.0}
Vint={}  # (F-index) per k: V_k[i,j,k,l]
Vk={k:np.zeros((n,n,n,n)) for k in (0,2,4)}
for i in range(n):
  for j in range(n):
    for kk in range(n):
      for ll in range(n):
        for k in (0,2,4):
          v=V2(k,so[i],so[j],so[kk],so[ll])
          if v!=0: Vk[k][i,j,kk,ll]=v
# cubic field one-electron matrix: octahedral harmonic Y40 + sqrt(5/14)(Y44+Y4-4)
def Yop(q):
    # matrix <l m|C^4_q|l m'> in orbital basis
    M=np.zeros((5,5))
    for a,m in enumerate(ms):
        for b,mp in enumerate(ms):
            M[a,b]=C(4,q,m,mp)
    return M
# use C^4 components (proportional to Y4q); octahedral: C40 + sqrt(5/14)(C44 + C4-4)
M0=Yop(0); M4=Yop(4); Mm4=Yop(-4)
Moct=M0+sqrt(5/14)*(M4+Mm4)
# eigen
w,_=np.linalg.eigh(Moct)
# need eg (2-fold) at +6, t2g (3-fold) at -4 after scaling; check degeneracies
print("raw eig",np.round(w,6))
