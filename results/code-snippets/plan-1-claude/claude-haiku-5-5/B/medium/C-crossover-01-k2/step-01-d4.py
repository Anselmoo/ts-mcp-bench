import numpy as np, itertools
from sympy.physics.wigner import wigner_3j, gaunt
from scipy.optimize import brentq
l=2
ms=list(range(-2,3))
# spin orbitals: (m, s) index
so=[(m,s) for m in ms for s in (1,-1)]
def C_me(m,k,q,mp):
    # <l m| C^k_q | l mp>, C^k_q = sqrt(4pi/(2k+1)) Y_kq ; Gaunt-based
    if m!=mp+q: return 0.0
    # <l m|C^k_q|l m'> = (-1)^(l-m) (l k l; -m q m') * (-1)^l (2l+1) (l k l;0 0 0)  [reduced element convention]
    return float((-1)**(l-m)*wigner_3j(l,k,l,-m,q,mp)*(-1)**l*(2*l+1)*wigner_3j(l,k,l,0,0,0))
def ang(k,a,c,b,d):
    # sum_q (-1)^q <a|C^k_q|c><b|C^k_-q|d>, a,b,c,d are m values
    tot=0.0
    for q in range(-k,k+1):
        tot+=(-1)**q*C_me(a,k,q,c)*C_me(b,k,-q,d)
    return tot
# Coulomb: V(a,b,c,d)= sum_k F^k ang  (spin-orbitals: spin delta on a-c, b-d)
def V(i,j,k_,l_,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[i],so[j],so[k_],so[l_]
    if sa!=sc or sb!=sd: return 0.0
    return sum(F[k]*ang(k,ma,mc,mb,md) for k in (0,2,4))
# one-electron cubic field: real orbitals in complex basis
# t2g: xy, yz, xz ; eg: z2, x2-y2 expressed in |m> basis
r2=np.sqrt(2)
h1=np.zeros((10,10),complex)
# Build cubic field one-particle operator in complex m basis: Dq*(-4 on t2g, +6 on eg)
# Use Y_2m: xz,yz etc. Represent via orbital vectors over m=-2..2
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
# real orbitals in complex basis (Condon-Shortley real combos)
orb={
 'z2': vec({0:1}),
 'x2y2': vec({2:1/r2,-2:1/r2}),
 'xy': vec({2:-1j/r2,-2:1j/r2}),
 'xz': vec({1:-1/r2,-1:1/r2}),
 'yz': vec({1:-1j/r2,-1:-1j/r2}),
}
# Cubic field matrix: -4Dq on t2g, +6Dq on eg (in units of Dq)
P=np.zeros((5,5),complex)
for name,w in [('xy',-4),('xz',-4),('yz',-4),('z2',6),('x2y2',6)]:
    v=orb[name]; P+=w*np.outer(v,v.conj())
def build(Dq,B,C):
    F4=441*C/35.0
    F2=(441*B+5*F4)/9.0
    F={0:0.0,2:F2,4:F4}
    # one-electron in spin-orbital basis
    H1=np.zeros((10,10),complex)
    for i,(m1,s1) in enumerate(so):
        for j,(m2,s2) in enumerate(so):
            if s1==s2: H1[i,j]=Dq*P[m1+2,m2+2]
    # 2-body
    Vt=np.zeros((10,10,10,10))
    for i,j,k_,l_ in itertools.product(range(10),repeat=4):
        Vt[i,j,k_,l_]=V(i,j,k_,l_,F).real if True else 0
    # build full Hamiltonian in Slater determinant basis of 4 electrons
    dets=list(itertools.combinations(range(10),4))
    idx={d:n for n,d in enumerate(dets)}
    N=len(dets); H=np.zeros((N,N))
    def sgn_apply(state,p):
        # annihilate orbital p from sorted tuple; return (sign, newstate) or None
        if p not in state: return None
        pos=state.index(p)
        return ((-1)**pos, tuple(x for x in state if x!=p))
    def create(state,p):
        if p in state: return None
        pos=sum(1 for x in state if x<p)
        new=tuple(sorted(state+(p,)))
        return ((-1)**pos,new)
    for n,d in enumerate(dets):
        # one-body
        for i in range(10):
            for j in range(10):
                if abs(H1[i,j])<1e-14: continue
                r=sgn_apply(d,j)
                if r is None: continue
                s1,st=r
                r2_=create(st,i)
                if r2_ is None: continue
                s2,st2=r2_
                H[idx[st2],n]+=s1*s2*H1[i,j].real
        # two-body: 1/2 sum V_{ijkl} c+_i c+_j c_l c_k ; V_{ijkl}=<ij|kl>
        for i,j,k_,l_ in itertools.product(range(10),repeat=4):
            v=Vt[i,j,k_,l_]
            if abs(v)<1e-12: continue
            # apply c_k then c_l (annihilate l first then k)
            r=sgn_apply(d,l_)
            if r is None: continue
            sa,st=r
            r=sgn_apply(st,k_)
            if r is None: continue
            sb,st=r
            r=create(st,j)
            if r is None: continue
            sc,st=r
            r=create(st,i)
            if r is None: continue
            sd,st=r
            H[idx[st],n]+=0.5*v*sa*sb*sc*sd
    # Sz, S2 for triplet selection: use total spin S^2
    Sz=np.array([sum(0.5*so[p][1] for p in d) for d in dets])
    return dets,H,Sz
