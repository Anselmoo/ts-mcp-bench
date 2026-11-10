mkdir -p /tmp/w && cat > /tmp/w/d2.py <<'EOF'
import numpy as np, itertools, sys
from sympy.physics.wigner import wigner_3j
from functools import lru_cache
from scipy.optimize import least_squares
l=2; MS=list(range(-2,3))
@lru_cache(None)
def w3(a,b,c,d,e,f): return float(wigner_3j(a,b,c,d,e,f))
def Vsp(F,ma,mb,mc,md,phase):
    s=0.0
    for k in (0,2,4):
        g=(2*l+1)**2*w3(l,k,l,0,0,0)**2
        t=0.0
        for q in range(-k,k+1):
            t+=(-1)**q*w3(l,k,l,-ma,q,mc)*w3(l,k,l,-mb,-q,md)
        s+=F[k]*g*t
    return s*(phase(ma,mb))
# spin-orbitals: index p = 2*(orb_index)+spin, spin 0=up,1=down
def build(F, h, phase):
    spo=[(m,s) for m in MS for s in (0,1)]
    N=len(spo)
    V=np.zeros((N,N,N,N))
    for p,(mp,sp) in enumerate(spo):
     for q,(mq,sq) in enumerate(spo):
      for r,(mr,sr) in enumerate(spo):
       for s_,(ms_,ss) in enumerate(spo):
        if sp==sr and sq==ss:
          V[p,q,r,s_]=Vsp(F,mp,mq,mr,ms_,phase)
    # two-electron states: pairs p<q
    st=list(itertools.combinations(range(N),2))
    idx={x:i for i,x in enumerate(st)}
    D=len(st); Hm=np.zeros((D,D))
    def apply_cc_c(occ,ops):
        # ops: list of ('c',i) creation or ('a',i) annihilation applied right-to-left
        return None
    # two-body matrix via antisymmetrized: <ij|H2|kl>=V_ijkl - V_ijlk for ordered dets
    for I,(i,j) in enumerate(st):
      for J,(k,l_) in enumerate(st):
        # H2 = 1/2 sum V_pqrs c+p c+q c_s c_r
        val=0.0
        for (p,q) in [(i,j)]:
            pass
        val = V[i,j,k,l_]-V[i,j,l_,k]
        Hm[I,J]+=val
    # one-body
    for I,(i,j) in enumerate(st):
      for J,(k,l_) in enumerate(st):
        val=0.0
        # <ij|h|kl> = h_ik d_jl - h_il d_jk + h_jl d_ik - h_jk d_il
        def hh(a,b):
            return h[a,b] if spo[a][1]==spo[b][1] else 0.0
        val = hh(i,k)*(j==l_) - hh(i,l_)*(j==k) + hh(j,l_)*(i==k) - hh(j,k)*(i==l_)
        Hm[I,J]+=val
    return Hm, st, spo
def hmat(Dq):
    Peg=np.zeros((5,5))
    Peg[2,2]=1.0
    for a in (0,4):
        for b in (0,4):
            Peg[a,b]=0.5 if (a!=2 and b!=2 and a!=b) else 0
    # eg: |0> and (|2>+|-2>)/sqrt2 : indices MS index: m=-2->0, m=2->4, m=0->2
    Peg=np.zeros((5,5))
    Peg[2,2]=1.0
    Peg[0,0]=0.5; Peg[4,4]=0.5; Peg[0,4]=0.5; Peg[4,0]=0.5
    hm=-4*Dq*np.eye(5)+10*Dq*Peg
    h=np.zeros((10,10))
    for p in range(5):
      for q in range(5):
        for s in (0,1):
          h[2*p+s,2*q+s]=hm[p,q]
    return h
EOF
echo ok