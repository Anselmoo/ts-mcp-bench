import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=784.;C=3699.
F4=C/35;F2=B+5*F4;F={0:0,2:49*F2,4:441*F4}
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # <m1|c^k_q|m2>
    q=m1-m2
    from sympy import sqrt,Rational
    return float((-1)**m1*sqrt(5*5)*gaunt(2,k,2,-m1,q,m2)*1) if abs(q)<=k else 0
# c^k(l m1,l m2)=(-1)^m1 *(2l+1)*3j(l k l;0 0 0)*3j(l k l;-m1 q m2); use gaunt normalization: gaunt=sqrt((5*(2k+1)*5)/4pi)*3j3j
import math
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,q,m2))
# <m1 m2|g|m3 m4> = sum_k F^k /(?) c^k(m1,m3)c^k(m4,m2)  (Slater: F^k = reduced*?), with ak
V=np.zeros((5,5,5,5))
for a,b_,cc,d in itertools.product(range(5),repeat=4):
    m1,m2,m3,m4=[x-2 for x in (a,b_,cc,d)]
    if m1+m2!=m3+m4: continue
    V[a,b_,cc,d]=sum(F[k]/ (1.0) *c(k,m1,m3)*c(k,m4,m2) for k in (2,4))
# V = <ab|g|cd> ; F^k here already in actual units (F2=49*...); fine
def run(Dq):
    # real orbs in complex basis idx m+2
    s=1/np.sqrt(2)
    def vec(d):
        v=np.zeros(5,complex)
        for m,x in d.items(): v[m+2]=x
        return v
    z2=vec({0:1}); x2=vec({2:s,-2:s}); xy=vec({2:-1j*s,-2:1j*s})
    xz=vec({1:s,-1:-s}); yz=vec({1:1j*s,-1:1j*s})
    h=sum(6*Dq*np.outer(v,v.conj()) for v in (z2,x2))+sum(-4*Dq*np.outer(v,v.conj()) for v in (xy,xz,yz))
    # spin orbitals index 2*o+s
    N=10
    H1=np.zeros((N,N),complex)
    for o1 in range(5):
        for o2 in range(5):
            for s_ in range(2): H1[2*o1+s_,2*o2+s_]=h[o1,o2]
    dets=list(itertools.combinations(range(N),7))
    idx={d:i for i,d in enumerate(dets)}
    H=np.zeros((120,120),complex); S2=np.zeros((120,120),complex)
    def ap(op,dag,state):
        # apply a^dag or a on tuple
        if dag:
            if op in state: return None
            pos=sum(1 for x in state if x<op); new=tuple(sorted(state+(op,)))
        else:
            if op not in state: return None
            pos=state.index(op); new=tuple(x for x in state if x!=op)
        return new,(-1)**pos
    def apply_ops(ops,state):
        sg=1
        for op,dag in reversed(ops):
            r=ap(op,dag,state)
            if r is None: return None
            state,s1=r; sg*=s1
        return state,sg
    for st in dets:
        j=idx[st]
        for p in range(N):
            for q in range(N):
                if abs(H1[p,q])>1e-12:
                    r=apply_ops([(p,1),(q,0)],st)
                    if r: H[idx[r[0]],j]+=H1[p,q]*r[1]
        for a,b_,cc,d in itertools.product(range(5),repeat=4):
            if V[a,b_,cc,d]==0: continue
            for s1 in range(2):
                for s2 in range(2):
                    # 1/2 sum <ab|cd> a+_a s1 a+_b s2 a_d s2 a_c s1
                    r=apply_ops([(2*a+s1,1),(2*b_+s2,1),(2*d+s2,0),(2*cc+s1,0)],st)
                    if r: H[idx[r[0]],j]+=0.5*V[a,b_,cc,d]*r[1]
        # S^2 = S-S+ + Sz(Sz+1)
        sz=sum(0.5 if x%2==0 else -0.5 for x in st)
        S2[j,j]+=sz*sz+sz*0  # placeholder
        # S-S+ : sum_{o,o'} a+_{o dn} a_{o up} a+_{o' up} a_{o' dn}
        for o in range(5):
            for o2 in range(5):
                r=apply_ops([(2*o+1,1),(2*o,0),(2*o2,1),(2*o2+1,0)],st)
                if r: S2[idx[r[0]],j]+=r[1]
        S2[j,j]+=sz
    return H,S2
import sys
for Dq in [1.45*B,2.45*B,3.0*B]:
    H,S2=run(Dq)
    # add Sz-adjust: S2 constructed as S-S+ + Sz^2+Sz
    # restrict to Sz=+1/2 ? diagonalize H + small*S2 jointly
    M=H+1e-3*S2
    w,v=np.linalg.eigh((M+M.conj().T)/2)
    w0=w.min()
    out=[]
    for i in range(120):
        s2=(v[:,i].conj()@S2@v[:,i]).real
        S=(-1+np.sqrt(1+4*s2))/2
        out.append((round((w[i]-w0)/B,3),round(S,1)))
    # unique with multiplicity (spin-orbital degenerate; Sz)
    from collections import Counter
    # keep only Sz=1/2? just print counts
    cnt=Counter(out)
    print(Dq/B,[ (k,v/(2*k[1]+1)) for k,v in sorted(cnt.items())][:8])
