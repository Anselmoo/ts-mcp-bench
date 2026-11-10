cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B=922.0; C=4156.0
F4=441*C/35; F2=441*B+5*F4
F={2:F2,4:F4}
ms=[-2,-1,0,1,2]
# spin orbitals: (m,s), s=+1/2 ->0, -1/2 ->1
so=[(m,s) for s in (0,1) for m in ms]
n=len(so)
def ang(ma,k,q,mc):
    # integral Y_{2,ma}^* Y_{k,q} Y_{2,mc}
    if ma-(-q)*0 is None: pass
    return complex(gaunt(2,k,2,-ma,q,mc))  # Y_{2,-ma}... handled below
def Yint(ma,k,q,mc):
    # int Y*_{2 ma} Y_{k q} Y_{2 mc}; use conj(Y_{2ma}) = (-1)^ma Y_{2,-ma}
    if q!=ma-mc and True:
        pass
    val=(-1)**ma*gaunt(2,k,2,-ma,q,mc)
    return float(val)
# Coulomb two-body matrix element <ab|V|cd> for spin orbitals
def V2(a,b,c,d):
    ma,sa=so[a]; mb,sb=so[b]; mc,sc=so[c]; md,sd=so[d]
    if sa!=sc or sb!=sd: return 0.0
    tot=0.0
    for k in (2,4):
        s=0.0
        for q in range(-k,k+1):
            # electron1: a* Y_kq c ; electron2: b* Y_{k,-q} d
            if abs(q)>0 and False: pass
            if (mc+q)!=ma or (md-q)!=mb: continue
            s+=(-1)**q*Yint(ma,k,q,mc)*Yint(mb,k,-q,md)
        tot+=F[k]*4*np.pi/(2*k+1)*s
    return tot
# one-electron cubic field in m basis
ct=[]
# eg: z2, x2-y2 ; t2g: xy,xz,yz as combos of |m>
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
r2=np.sqrt(2)
orbs=[(6,vec({0:1})),(6,vec({2:1/r2,-2:1/r2})),
      (-4,vec({2:1/(1j*r2),-2:-1/(1j*r2)})),
      (-4,vec({1:-1/r2,-1:1/r2})),
      (-4,vec({1:1j/r2,-1:1j/r2}))]
# check orthonormality
M=np.array([o[1] for o in orbs])
assert np.allclose(M.conj()@M.T,np.eye(5)), M.conj()@M.T
def hmat(Dq):
    h=np.zeros((5,5),complex)
    for e,v in orbs:
        h+= Dq*e*np.outer(v,v.conj())
    return h
# build determinant basis
def dets(nup,ndn):
    up=[i for i in range(5)]; dn=[i+5 for i in range(5)]
    out=[]
    for A in itertools.combinations(up,nup):
        for Bb in itertools.combinations(dn,ndn):
            out.append(tuple(sorted(A+Bb)))
    return out
def build(Dq,occ):
    h=hmat(Dq)
    # full h in spin-orbital index
    H1=np.zeros((n,n),complex)
    for s in (0,1):
        for i in range(5):
            for j in range(5):
                H1[i+5*s,j+5*s]=h[i,j]
    # two-body
    V=np.zeros((n,n,n,n))
    for a,b,c,d in itertools.product(range(n),repeat=4):
        V[a,b,c,d]=V2(a,b,c,d)
    idx={d:i for i,d in enumerate(occ)}
    N=len(occ); Hm=np.zeros((N,N),complex)
    for I,dI in enumerate(occ):
        for J,dJ in enumerate(occ):
            # general Slater-Condon via second quantization
            Hm[I,J]=opmat(dI,dJ,H1,V)
    return Hm
def apply(state,ops):
    # state: sorted tuple; ops: list of (type,index) applied right to left
    pass
def opmat(bra,ket,H1,V):
    # <bra| H |ket> where H = sum H1_ij a+_i a_j + 1/2 sum V_abcd a+_a a+_b a_d a_c
    tot=0j
    ket_l=list(ket)
    # one-body
    for i in range(n):
        for j in range(n):
            if H1[i,j]==0: continue
            r=annih(ket_l,j)
            if r is None: continue
            s1,st=r
            r2_=create(st,i)
            if r2_ is None: continue
            s2,st2=r2_
            if tuple(st2)==bra: tot+=H1[i,j]*s1*s2
    for a,b,c,d in itertools.product(range(n),repeat=4):
        if V[a,b,c,d]==0: continue
        r=annih(ket_l,c)
        if r is None: continue
        s1,st=r
        r=annih(st,d)
        if r is None: continue
        s2,st=r
        r=create(st,b)
        if r is None: continue
        s3,st=r
        r=create(st,a)
        if r is None: continue
        s4,st=r
        if tuple(st)==bra: tot+=0.5*V[a,b,c,d]*s1*s2*s3*s4
    return tot
def annih(st,j):
    if j not in st: return None
    p=st.index(j)
    return ((-1)**p, [x for x in st if x!=j])
def create(st,j):
    if j in st: return None
    p=sum(1 for x in st if x<j)
    new=sorted(st+[j])
    return ((-1)**p,new)
def energies(Dq,nup,ndn):
    occ=dets(nup,ndn)
    Hm=build(Dq,occ)
    return np.sort(np.linalg.eigvalsh((Hm+Hm.conj().T)/2))
if __name__=="__main__":
    import sys
    for Dq in [0.0,1000.0]:
        q=energies(Dq,5,2); d=energies(Dq,4,3)
        print(Dq, q[:4], d[:6])
EOF
cd /tmp && time python3 d7.py