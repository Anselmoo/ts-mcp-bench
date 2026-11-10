import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N as sN
from functools import lru_cache
from scipy.optimize import least_squares
from math import pi

# spatial m=-2..2 ; spin-orbital index i = 2*(m+2)+s, s=0 up, 1 down
NSO=10
@lru_cache(None)
def gnt(l1,m1,l2,m2,l3,m3):
    if m1+m2+m3!=0: return 0.0
    return float(sN(gaunt(l1,l2,l3,m1,m2,m3),15))

def ang(k,mi,mj,mk,ml):
    # V_{ij,kl}: sum_q (4pi/(2k+1)) X1 X2 ; returns sum over q (without 4pi/(2k+1))
    tot=0.0
    for q in range(-k,k+1):
        X1=(-1)**(mi+q)*gnt(2,-mi,k,-q,2,mk)
        X2=(-1)**mj*gnt(2,-mj,k,q,2,ml)
        tot+=X1*X2
    return tot*4*pi/(2*k+1)

def Vspatial(mi,mj,mk,ml,F):
    return sum(F[k]*ang(k,mi,mj,mk,ml) for k in (2,4))

def build(Dq,B,C):
    F={2:441*B+63*C,4:441*C/35.0}
    # one-electron: h = 10Dq P_eg (spatial m basis), constant dropped
    h=np.zeros((5,5))
    idx=lambda m: m+2
    h[idx(0),idx(0)]+=1
    for a in (2,-2):
        for b in (2,-2):
            h[idx(a),idx(b)]+=0.5
    h*=10*Dq
    # spin-orbital one-electron
    H1=np.zeros((NSO,NSO))
    for m1 in range(-2,3):
        for m2 in range(-2,3):
            for s in (0,1):
                H1[2*(m1+2)+s,2*(m2+2)+s]=h[idx(m1),idx(m2)]
    # two-electron <ij|V|kl> spin-orbital
    V=np.zeros((NSO,NSO,NSO,NSO))
    for i in range(NSO):
        for j in range(NSO):
            for k in range(NSO):
                for l in range(NSO):
                    si,mi=i%2,i//2-2; sj,mj=j%2,j//2-2
                    sk,mk=k%2,k//2-2; sl,ml=l%2,l//2-2
                    if si!=sk or sj!=sl: continue
                    V[i,j,k,l]=Vspatial(mi,mj,mk,ml,F)
    # basis: 7 electrons
    basis=[sum(1<<i for i in c) for c in itertools.combinations(range(NSO),7)]
    index={b:n for n,b in enumerate(basis)}
    D=len(basis)
    def apply_cdag_c(a,b,state):
        # c†_a c_b |state>
        if not (state>>b)&1: return None,0
        sgn=(-1)**bin(state & ((1<<b)-1)).count('1')
        st=state ^ (1<<b)
        if (st>>a)&1: return None,0
        sgn*= (-1)**bin(st & ((1<<a)-1)).count('1')
        return st|(1<<a), sgn
    def apply_cdag_cdag_c_c(a,b,c,d,state):
        # c†_a c†_b c_d c_c   (note order: c_c applied first? we use c†_a c†_b c_d c_c)
        st,s1=apply_cdag_c_single(c,state)  # c_c
        if st is None: return None,0
        st,s2=apply_cdag_c_single(d,st)     # c_d
        if st is None: return None,0
        st,s3=cdag_single(b,st)
        if st is None: return None,0
        st,s4=cdag_single(a,st)
        if st is None: return None,0
        return st, s1*s2*s3*s4
    def apply_cdag_c_single(x,state):
        if not (state>>x)&1: return None,0
        sgn=(-1)**bin(state & ((1<<x)-1)).count('1')
        return state ^ (1<<x), sgn
    def cdag_single(x,state):
        if (state>>x)&1: return None,0
        sgn=(-1)**bin(state & ((1<<x)-1)).count('1')
        return state | (1<<x), sgn
    H=np.zeros((D,D))
    for n,b in enumerate(basis):
        # one-electron
        for a in range(NSO):
            for c in range(NSO):
                if H1[a,c]==0: continue
                st,s=apply_cdag_c(a,c,b)
                if st is None: continue
                H[index[st],n]+=H1[a,c]*s
        # two-electron: 1/2 sum V_{ijkl} c†_i c†_j c_l c_k
        for i in range(NSO):
            for j in range(NSO):
                if i==j: continue
                for k in range(NSO):
                    for l in range(NSO):
                        if k==l: continue
                        v=V[i,j,k,l]
                        if v==0: continue
                        st,s=apply_cdag_cdag_c_c(i,j,l,k,b)
                        if st is None: continue
                        H[index[st],n]+=0.5*v*s
    # S^2
    Sz=np.zeros((D,D)); Sp=np.zeros((D,D))
    for n,b in enumerate(basis):
        nu=sum(((b>>(2*m))&1) for m in range(5)); nd=sum(((b>>(2*m+1))&1) for m in range(5))
        Sz[n,n]=0.5*(nu-nd)
        for m in range(5):
            st,s=apply_cdag_c(2*m,2*m+1,b)  # S+ = c†_up c_down
            if st is not None: Sp[index[st],n]+=s
    Sm=Sp.T
    S2=Sm@Sp+Sz@Sz+Sz
    return H,S2,basis

def levels(Dq,B,C):
    H,S2,_=build(Dq,B,C)
    M=H+1e5*S2
    w,v=np.linalg.eigh(M)
    out=[]
    for e,vec in zip(w,v.T):
        s2=vec@S2@vec
        Hexp=vec@H@vec
        S=(-1+np.sqrt(1+4*s2))/2
        out.append((Hexp,round(S*2)/2))
    return sorted(out)
if __name__=="__main__":
    import sys
    lv=levels(1000,800,3200)
    gs=lv[0][0]
    for e,S in lv:
        if e-gs<40000: print(round(e-gs,1),S)
