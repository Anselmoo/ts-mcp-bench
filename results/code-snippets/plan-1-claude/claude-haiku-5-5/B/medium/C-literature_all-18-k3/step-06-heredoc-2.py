import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq, fsolve
from functools import lru_cache
l=2; ms=list(range(-2,3))
@lru_cache(None)
def w3(a,b,c,d,e,f): return float(wigner_3j(a,b,c,d,e,f))
def tensor(k,q,m1,m3):
    if m1-m3!=q: return 0.0
    red=(-1)**l*(2*l+1)*w3(l,k,l,0,0,0)
    return (-1)**(l-m1)*w3(l,k,l,-m1,q,m3)*red
def cmat(k,q): return np.array([[tensor(k,q,m1,m3) for m3 in ms] for m1 in ms])
Vcf = cmat(4,0)+np.sqrt(5/14)*(cmat(4,4)+cmat(4,-4))
Mcf = 21.0*Vcf   # eg=+6, t2g=-4 (units of Dq)
# spin-orbitals: p = 2*orb+s, s=0 up, 1 down
SO=[(i,s) for i in range(5) for s in (0,1)]
# Coulomb angular coefficients a_k(m1,m2,m3,m4)=sum_q (-1)^q <m1|C^k_q|m3><m2|C^k_-q|m4>
def ang(k,m1,m2,m3,m4):
    tot=0.0
    for q in range(-k,k+1):
        tot+=(-1)**q*tensor(k,q,m1,m3)*tensor(k,-q,m2,m4)
    return tot
def Vint(F,a,b,c,d):
    (ia,sa),(ib,sb),(ic,sc),(id_,sd)=a,b,c,d
    if sa!=sc or sb!=sd: return 0.0
    m1,m2,m3,m4=ms[ia],ms[ib],ms[ic],ms[id_]
    return sum(F[k]*ang(k,m1,m2,m3,m4) for k in F)
def build(B,C):
    # Racah: B=(9F2-5F4)/441, C=35F4/441 -> solve F2,F4
    F4=441*C/35.0
    F2=(441*B+5*F4)/9.0
    F={0:0.0,2:F2,4:F4}
    # basis: 8-electron determinants
    basis=[]
    for occ in itertools.combinations(range(10),8): basis.append(occ)
    idx={o:i for i,o in enumerate(basis)}
    N=len(basis); H=np.zeros((N,N))
    # one-electron
    def apply_and_sign(occ, ops):
        # ops list of ('c'|'a', p) applied right-to-left as given; returns (sign, newocc) or None
        occ=list(occ); sign=1
        for typ,p in reversed(ops):
            if typ=='a':   # annihilate
                if p not in occ: return None
                pos=occ.index(p); sign*=(-1)**pos; occ.pop(pos)
            else:
                if p in occ: return None
                # insert in sorted position
                pos=sum(1 for x in occ if x<p); sign*=(-1)**pos; occ.insert(pos,p)
        return sign, tuple(sorted(occ))
    for j,occ in enumerate(basis):
        # one-body: sum h_ab c^+_a c_b
        for a in range(10):
            for b in range(10):
                ia,sa=SO[a]; ib,sb=SO[b]
                if sa!=sb: continue
                h=Mcf[ms.index(ia) if False else ia, ib]
                if abs(h)<1e-14: continue
                r=apply_and_sign(occ,[('c',a),('a',b)])
                if r: H[idx[r[1]],j]+=h*r[0]
        # two-body: 1/2 sum V_abcd c+_a c+_b c_d c_c
        for a in range(10):
          for b in range(10):
            if a==b: continue
            for c in range(10):
              for d in range(10):
                if c==d: continue
                v=Vint(F,SO[a],SO[b],SO[c],SO[d])
                if abs(v)<1e-14: continue
                r=apply_and_sign(occ,[('c',a),('c',b),('a',d),('a',c)])
                if r: H[idx[r[1]],j]+=0.5*v*r[0]
    # S^2
    Sz=np.zeros(N); Sp=np.zeros((N,N))
    S2=np.zeros((N,N))
    for j,occ in enumerate(basis):
        nup=sum(1 for p in occ if p%2==0); ndn=8-nup
        Sz[j]=0.5*(nup-ndn)
        for i in range(5):
            # S+ = sum c+_{i,up} c_{i,dn}
            r=apply_and_sign(occ,[('c',2*i),('a',2*i+1)])
            if r: Sp[idx[r[1]],j]+=r[0]
    Sm=Sp.T
    S2=Sm@Sp+np.diag(Sz*(Sz+1)) if False else None
    Sz_m=np.diag(Sz)
    S2=Sm@Sp+Sz_m@Sz_m+Sz_m
    return H,S2
def spectrum(Dq,B,C):
    H,S2=build(B,C)
    return H,S2
