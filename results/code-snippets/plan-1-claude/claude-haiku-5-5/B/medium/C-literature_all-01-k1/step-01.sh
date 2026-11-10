
cat << 'EOF' > /tmp/ni.py
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import fsolve
from math import factorial
# d orbitals m=-2..2 complex Y_2m
ms=[-2,-1,0,1,2]
# quadrature on sphere
xg,wg=np.polynomial.legendre.leggauss(20)
nphi=40
th=np.arccos(xg); ph=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(wg,np.ones(nphi))*2*np.pi/nphi
def Y(l,m,t,p): return sph_harm(m,l,p,t)  # scipy: sph_harm(m,n,azimuth,polar)
Yd={m:Y(2,m,TH,PH) for m in ms}
# angular integrals: ang[k][a,b,c,d] = <ab|P_k|cd> 4pi/(2k+1) sum_q <a|Y_kq*|c><b|Y_kq|d>
def Ykq(k,q,t,p): return sph_harm(q,k,p,t)
ang={}
for k in [0,2,4]:
    A=np.zeros((5,5,5,5),complex)
    for q in range(-k,k+1):
        Yk=Ykq(k,q,TH,PH)
        # matrix X_ac = int Y_a^* Yk^* Y_c
        X=np.zeros((5,5),complex)
        for i,a in enumerate(ms):
            for j,c in enumerate(ms):
                X[i,j]=np.sum(W*np.conj(Yd[a])*np.conj(Yk)*Yd[c])
        Z=np.zeros((5,5),complex)
        for i,b in enumerate(ms):
            for j,d in enumerate(ms):
                Z[i,j]=np.sum(W*np.conj(Yd[b])*Yk*Yd[d])  # <b|Y_kq|d>
        A+=np.einsum('ac,bd->abcd',X,Z)
    ang[k]=A*4*np.pi/(2*k+1)
# spin-orbitals: index (m,s)
so=[(m,s) for m in ms for s in (1,-1)]
N=len(so)
# 8 electrons: choose 8 of 10 spin orbitals -> holes; use electrons directly
states=list(itertools.combinations(range(N),8))
idx={s:i for i,s in enumerate(states)}
def apply_c(st,i):  # annihilate
    if i not in st: return None,0
    pos=st.index(i); sign=(-1)**pos
    return tuple(x for x in st if x!=i),sign
def apply_cdag(st,i):
    if i in st: return None,0
    pos=sum(1 for x in st if x<i); sign=(-1)**pos
    return tuple(sorted(st+(i,))),sign
def opmat(Vfun):
    M=np.zeros((len(states),len(states)),complex)
    return M
# build two-body operator matrices for each k: H_k = 1/2 sum_{abcd} <ab|V|cd> c+_a c+_b c_d c_c
def twobody(k):
    H=np.zeros((len(states),len(states)),complex)
    A=ang[k]
    for si,st in enumerate(states):
        for c_ in range(N):
            for d_ in range(N):
                # c_c first (rightmost), then c_d
                s1,g1=apply_c(st,d_)
                if s1 is None: continue
                s2,g2=apply_c(s1,c_)
                if s2 is None: continue
                for a_ in range(N):
                    for b_ in range(N):
                        ma,sa=so[a_]; mb,sb=so[b_]; mc,sc=so[c_]; md,sd=so[d_]
                        # spin delta
                        if sa!=sc or sb!=sd: 
                            # direct term requires spin a=c, b=d
                            pass
                        val=0
                        # direct: <ab|V|cd> with spins a=c, b=d
                        if sa==sc and sb==sd:
                            val+=A[ms.index(ma),ms.index(mb),ms.index(mc),ms.index(md)]
                        # exchange: <ab|V|dc>: spins a=d,b=c
                        if sa==sd and sb==sc:
                            val-=A[ms.index(ma),ms.index(mb),ms.index(md),ms.index(mc)]
                        if val==0: continue
                        s3,g3=apply_cdag(s2,b_)
                        if s3 is None: continue
                        s4,g4=apply_cdag(s3,a_)
                        if s4 is None: continue
                        H[idx[s4],si]+=0.5*val*g1*g2*g3*g4
    return H
Hk={k:twobody(k) for k in [2,4]}
# one-body crystal field Td: e (m=0,±2 real combos) -6Dq, t2 +4Dq. Use cubic: in complex basis, Td field
# build via real orbitals: dz2, dx2-y2 (e) lower; dxy,dxz,dyz (t2) higher.
# Use Ylm: e = {z^2 (m=0), x2-y2 (combo of m=±2)}, t2 = {xy,xz,yz}
# Build cubic potential numerically: V = Dq* (sum over Td-like harmonic) -> simpler: define one-electron matrix in real basis
import numpy as np
r2=np.sqrt(2)
# real d orbitals in terms of complex m basis: coefficient vectors over ms=[-2..2]
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[ms.index(m)]=c
    return v
dz2=vec({0:1})
dx2y2=vec({2:1/r2,-2:1/r2})
dxy=vec({2:-1j/r2,-2:1j/r2})
dxz=vec({1:-1/r2,-1:1/r2})
dyz=vec({1:-1j/r2,-1:-1j/r2})
orbs_e=[dz2,dx2y2]; orbs_t=[dxz,dyz,dxy]
# one-electron matrix: e -> -6Dq, t2 -> +4Dq  (Td, electron)
h1=np.zeros((5,5),complex)
for v in orbs_e: h1+=-6*np.outer(v,v.conj())
for v in orbs_t: h1+=4*np.outer(v,v.conj())
def onebody(h):
    H=np.zeros((len(states),len(states)),complex)
    for si,st in enumerate(states):
        for a_ in range(N):
            for c_ in range(N):
                ma,sa=so[a_]; mc,sc=so[c_]
                if sa!=sc: continue
                val=h[ms.index(ma),ms.index(mc)]
                if abs(val)<1e-12: continue
                s1,g1=apply_c(st,c_)
                if s1 is None: continue
                s2,g2=apply_cdag(s1,a_)
                if s2 is None: continue
                H[idx[s2],si]+=val*g1*g2
    return H
H1=onebody(h1)
# Spin-triplet check via S^2
def S2mat():
    Sz=np.zeros(len(states)); 
    for i,st in enumerate(states): Sz[i]=sum(so[x][1] for x in st)/2
    return Sz
np.save('/tmp/H1.npy',H1)
import pickle
pickle.dump((H1,Hk,states),open('/tmp/mats.pkl','wb'))
# Sz=1 subspace (2 unpaired-ish) -> triplet states: Sz=1 has total spin S up to 1 for d8 ; use S2 operator
Sz=np.array([sum(so[x][1] for x in st)/2 for st in states])
# Build S^2 = S_-S_+ + Sz^2 + Sz; S_+ = sum c+_{m,up} c_{m,down}
def Splus():
    M=np.zeros((len(states),len(states)),complex)
    for si,st in enumerate(states):
        for m in ms:
            a=so.index((m,1)); b=so.index((m,-1))
            s1,g1=apply_c(st,b)
            if s1 is None: continue
            s2,g2=apply_cdag(s1,a)
            if s2 is None: continue
            M[idx[s2],si]+=g1*g2
    return M
Sp=Splus(); Sm=Sp.conj().T
S2=Sm@Sp+np.diag(Sz**2+Sz)
pickle.dump(S2,open('/tmp/S2.pkl','wb'))
print("built", len(states))
EOF
cd /tmp && timeout 900 python3 ni.py
