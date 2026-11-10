cat << 'EOF' > run.py
import numpy as np, itertools, sys
from d7 import *
from scipy.optimize import least_squares
dets=[sum(1<<i for i in c) for c in itertools.combinations(range(N),7)]
idx={d:n for n,d in enumerate(dets)}
def apply_ops(state_bits, ops):
    # ops: list of (type,i) applied right-to-left: ops[-1] acts first; type 'c' annihilate, 'd' create
    b=state_bits; sign=1
    for typ,i in reversed(ops):
        occ=(b>>i)&1
        # sign = (-1)^(number of occupied orbitals below i)
        below=bin(b & ((1<<i)-1)).count('1')
        if typ=='c':
            if not occ: return None,0
            b&=~(1<<i)
        else:
            if occ: return None,0
            b|=(1<<i)
        if below%2: sign=-sign
    return b,sign
def Hmat(Dq,F0,F2,F4):
    h,g=build(Dq,F0,F2,F4)
    H=np.zeros((len(dets),len(dets)),complex)
    nz=[(i,j,k,l) for i in range(N) for j in range(N) for k in range(N) for l in range(N) if abs(g[i,j,k,l])>1e-12]
    for n,d in enumerate(dets):
        for i in range(N):
            for j in range(N):
                if abs(h[i,j])<1e-14: continue
                b,s=apply_ops(d,[('d',i),('c',j)])
                if b is None: continue
                H[idx[b],n]+=s*h[i,j]
        for (i,j,k,l) in nz:
            # 1/2 sum g_ijkl c_i^dag c_j^dag c_l c_k
            b,s=apply_ops(d,[('d',i),('d',j),('c',l),('c',k)])
            if b is None: continue
            H[idx[b],n]+=0.5*s*g[i,j,k,l]
    return H
# spin operator S^2
def S2():
    # Sz and S+ S-
    n=len(dets)
    Sz=np.zeros(n); Sp=np.zeros((n,n))
    for x,d in enumerate(dets):
        Sz[x]=sum((0.5 if so[i][1]==0 else -0.5) for i in range(N) if d>>i&1)
    for x,d in enumerate(dets):
        for m in ms:
            up=2*(m+2)+0; dn=2*(m+2)+1
            if (d>>dn)&1 and not (d>>up)&1:
                b,s=apply_ops(d,[('d',up),('c',dn)])
                Sp[idx[b],x]+=s
    S2m=Sp.T@Sp + np.diag(Sz)**2 - np.diag(Sz)  # S- S+ = S^2 - Sz^2 - Sz ; S^2 = S-S+ + Sz^2 + Sz
    S2m=Sp.T@Sp + np.diag(Sz**2) + np.diag(Sz)  # S^2 = S- S+ + Sz^2 + Sz  (S- S+ = Sp.T@Sp)
    return S2m
S2op=S2()
def levels(Dq,F0,F2,F4):
    H=Hmat(Dq,F0,F2,F4).real
    w,v=np.linalg.eigh(H)
    S=np.real(np.einsum('in,ij,jn->n',v,S2op,v))
    return w,S
if __name__=="__main__":
    w,S=levels(1000,0,1000,600)
    import collections
    print(collections.Counter(np.round(S*4)/4))
EOF
python3 run.py