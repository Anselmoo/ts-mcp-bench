mkdir -p /tmp/ts && cat > /tmp/ts/ts.py << 'EOF'
import numpy as np, itertools, sys
from sympy.physics.wigner import wigner_3j
from scipy.linalg import expm
from functools import lru_cache

l=2
ms=list(range(-l,l+1))
NO=10  # spin-orbitals: idx = s*5 + (m+2), s=0 up, 1 down
def so(m,s): return s*5+(m+2)
spin_of=[0]*5+[1]*5
m_of=[m for s in range(2) for m in ms]

@lru_cache(None)
def w3(j1,j2,j3,m1,m2,m3):
    return float(wigner_3j(j1,j2,j3,m1,m2,m3))
def Cmat(k,q):
    M=np.zeros((5,5))
    red=(-1)**l*(2*l+1)*w3(l,k,l,0,0,0)
    for i,m in enumerate(ms):
        for j,mp in enumerate(ms):
            if -m+q+mp!=0: continue
            M[i,j]=(-1)**(l-m)*w3(l,k,l,-m,q,mp)*red
    return M

def coulomb_tensor(F):  # F: dict k->F^k ; returns G[a,b,c,d]=<ab|1/r|cd>
    G=np.zeros((NO,NO,NO,NO))
    for k,Fk in F.items():
        if Fk==0: continue
        ang=np.zeros((5,5,5,5))
        for q in range(-k,k+1):
            Cq=Cmat(k,q); Cmq=Cmat(k,-q)
            ang+= (-1)**q*np.einsum('ac,bd->abcd',Cq,Cmq)
        for a,b,c,d in itertools.product(range(NO),repeat=4):
            if spin_of[a]!=spin_of[c] or spin_of[b]!=spin_of[d]: continue
            G[a,b,c,d]+=Fk*ang[a%5,b%5,c%5,d%5]
    return G

def fock_basis(N):
    states=[sum(1<<i for i in c) for c in itertools.combinations(range(NO),N)]
    idx={s:i for i,s in enumerate(states)}
    return states,idx

def apply_ops(state, ops):
    # ops: list of ('c',i) or ('a',i) applied right to left: ops[-1] acts first
    s=state; sign=1
    for typ,i in reversed(ops):
        occ=(s>>i)&1
        if typ=='c':
            if occ: return None,0
            sign*= (-1)**bin(s & ((1<<i)-1)).count('1')
            s|=(1<<i)
        else:
            if not occ: return None,0
            sign*= (-1)**bin(s & ((1<<i)-1)).count('1')
            s&=~(1<<i)
    return s,sign

def build_ops(N, h1, G):
    states,idx=fock_basis(N); D=len(states)
    H=np.zeros((D,D),dtype=complex)
    # one-body
    for I,s in enumerate(states):
        for i in range(NO):
            for j in range(NO):
                if h1[i,j]==0: continue
                t,sg=apply_ops(s,[('c',i),('a',j)])
                if t is None: continue
                H[idx[t],I]+=h1[i,j]*sg
        for a,b,c,d in zip(*np.nonzero(np.abs(G)>1e-12)):
            # 1/2 G_abcd a+_a a+_b a_d a_c
            t,sg=apply_ops(s,[('c',a),('c',b),('a',d),('a',c)])
            if t is None: continue
            H[idx[t],I]+=0.5*G[a,b,c,d]*sg
    return states,idx,H

def spin_ops(N):
    states,idx=fock_basis(N); D=len(states)
    Sz=np.zeros((D,D)); Sp=np.zeros((D,D))
    for I,s in enumerate(states):
        nup=sum(1 for m in range(5) if (s>>so(ms[m],0))&1)
        ndn=sum(1 for m in range(5) if (s>>so(ms[m],1))&1)
        Sz[I,I]=(nup-ndn)/2
        for m in range(5):
            t,sg=apply_ops(s,[('c',so(ms[m],0)),('a',so(ms[m],1))])
            if t is not None: Sp[idx[t],I]+=sg
    Sm=Sp.T
    S2=Sm@Sp+Sz@Sz+Sz
    return S2

def single_particle_rot(Rm):  # Rm 5x5 unitary in m basis -> 10x10 spin-diagonal
    u=np.zeros((NO,NO),dtype=complex)
    for s in range(2):
        for i in range(5):
            for j in range(5):
                u[s*5+i,s*5+j]=Rm[i,j]
    return u

def compound(u,N,states,idx):
    D=len(states); U=np.zeros((D,D),dtype=complex)
    subsets=[[i for i in range(NO) if (s>>i)&1] for s in states]
    for I,A in enumerate(subsets):
        for J,B in enumerate(subsets):
            U[I,J]=np.linalg.det(u[np.ix_(A,B)])
    return U
EOF
cd /tmp/ts && cat > test_d2.py << 'EOF'
from ts import *
F2,F4=1.0,0.6
F={0:0.0,2:F2,4:F4}
G=coulomb_tensor(F)
states,idx,H=build_ops(2,np.zeros((10,10)),G)
w=np.linalg.eigvalsh(H)
B=(9*F2-5*F4)/441; C=35*F4/441
print("B,C",B,C)
vals=np.unique(np.round(w,6))
print(vals, len(w))
print("expected 3F ~ ",vals[0],"3P-3F/B:",(vals[np.argmin(abs(vals-vals[0]-15*B))] if False else None))
EOF
python3 test_d2.py 2>&1 | grep -v -i matplotlib