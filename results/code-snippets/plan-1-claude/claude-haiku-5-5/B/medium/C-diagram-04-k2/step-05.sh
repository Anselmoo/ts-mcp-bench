rm -f testfile && mkdir -p ts && cd ts && cat > ts.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from functools import lru_cache

l=2
ms=list(range(-l,l+1))
NO=10
def so(m,s): return s*5+(m+2)
spin_of=[0]*5+[1]*5

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

def coulomb_tensor(F):
    G=np.zeros((NO,NO,NO,NO))
    for k,Fk in F.items():
        if Fk==0: continue
        ang=np.zeros((5,5,5,5))
        for q in range(-k,k+1):
            ang+= (-1)**q*np.einsum('ac,bd->abcd',Cmat(k,q),Cmat(k,-q))
        for a,b,c,d in itertools.product(range(NO),repeat=4):
            if spin_of[a]!=spin_of[c] or spin_of[b]!=spin_of[d]: continue
            G[a,b,c,d]+=Fk*ang[a%5,b%5,c%5,d%5]
    return G

def fock_basis(N):
    states=[sum(1<<i for i in c) for c in itertools.combinations(range(NO),N)]
    return states,{s:i for i,s in enumerate(states)}

def apply_ops(state, ops):
    s=state; sign=1
    for typ,i in reversed(ops):
        occ=(s>>i)&1
        if typ=='c':
            if occ: return None,0
        else:
            if not occ: return None,0
        sign*= (-1)**bin(s & ((1<<i)-1)).count('1')
        s = s|(1<<i) if typ=='c' else s&~(1<<i)
    return s,sign

def build_H(N, h1, G):
    states,idx=fock_basis(N); D=len(states)
    H=np.zeros((D,D),dtype=complex)
    nz=list(zip(*np.nonzero(np.abs(G)>1e-12)))
    for I,s in enumerate(states):
        for i in range(NO):
            for j in range(NO):
                if abs(h1[i,j])<1e-14: continue
                t,sg=apply_ops(s,[('c',i),('a',j)])
                if t is not None: H[idx[t],I]+=h1[i,j]*sg
        for a,b,c,d in nz:
            t,sg=apply_ops(s,[('c',a),('c',b),('a',d),('a',c)])
            if t is not None: H[idx[t],I]+=0.5*G[a,b,c,d]*sg
    return states,idx,H

def spin_S2(N):
    states,idx=fock_basis(N); D=len(states)
    Sz=np.zeros((D,D)); Sp=np.zeros((D,D))
    for I,s in enumerate(states):
        nup=sum((s>>so(m,0))&1 for m in ms)
        ndn=sum((s>>so(m,1))&1 for m in ms)
        Sz[I,I]=(nup-ndn)/2
        for m in ms:
            t,sg=apply_ops(s,[('c',so(m,0)),('a',so(m,1))])
            if t is not None: Sp[idx[t],I]+=sg
    return Sp.T@Sp+Sz@Sz+Sz

def compound(u,states):
    D=len(states); U=np.zeros((D,D),dtype=complex)
    subs=[[i for i in range(NO) if (s>>i)&1] for s in states]
    for I,A in enumerate(subs):
        for J,Bs in enumerate(subs):
            U[I,J]=np.linalg.det(u[np.ix_(A,Bs)])
    return U

def spin_diag(Rm):
    u=np.zeros((NO,NO),dtype=complex)
    for s in range(2):
        u[s*5:s*5+5, s*5:s*5+5]=Rm
    return u
EOF
cat > test_d2.py << 'EOF'
from ts import *
F2,F4=1.0,0.6
G=coulomb_tensor({0:0.0,2:F2,4:F4})
states,idx,H=build_H(2,np.zeros((10,10)),G)
S2=spin_S2(2)
w,v=np.linalg.eigh(H+100*S2)
B=(9*F2-5*F4)/441; C=35*F4/441
out=[]
for e,vec in zip(w,v.T):
    S=(-1+np.sqrt(1+4*np.real(vec.conj()@S2@vec)))/2
    out.append((round(e-100*S*(S+1),6),round(S,2)))
import collections
c=collections.Counter(out)
for k in sorted(c): print(k,c[k])
print("B",B,"C",C)
EOF
python3 test_d2.py 2>&1 | grep -v -i matplotlib