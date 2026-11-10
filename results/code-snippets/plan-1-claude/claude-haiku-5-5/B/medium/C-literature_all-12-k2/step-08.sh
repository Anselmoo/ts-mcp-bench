cat > fock.py << 'EOF'
import numpy as np, itertools
from ff import build_V, build_h, NS
def apply_ops(state, ops):
    # ops: list of (idx, dag) applied right-to-left (last in list acts first)
    occ=list(state); sign=1
    for idx,dag in reversed(ops):
        if dag:
            if idx in occ: return None,0
            # insert idx: sign = (-1)^(number of occupied below idx)
            n=sum(1 for o in occ if o<idx)
            sign*= (-1)**n
            occ.append(idx); occ.sort()
        else:
            if idx not in occ: return None,0
            n=sum(1 for o in occ if o<idx)
            sign*= (-1)**n
            occ.remove(idx)
    return tuple(occ),sign
def hamiltonian(N, h, V, basis=None):
    if basis is None:
        basis=list(itertools.combinations(range(NS),N))
    idx={s:i for i,s in enumerate(basis)}
    D=len(basis)
    H=np.zeros((D,D),complex)
    for j,s in enumerate(basis):
        # one-body
        for a in range(NS):
            for b in range(NS):
                if abs(h[a,b])<1e-14: continue
                t,sg=apply_ops(s,[(a,True),(b,False)])
                if t is None: continue
                H[idx[t],j]+=h[a,b]*sg
        # two-body: 1/2 sum V[a,b,c,d] a+_a a+_b a_d a_c
        for a,b,c,d in itertools.product(range(NS),repeat=4):
            v=V[a,b,c,d]
            if abs(v)<1e-14: continue
            if a==b or c==d: continue
            t,sg=apply_ops(s,[(a,True),(b,True),(d,False),(c,False)])
            if t is None: continue
            H[idx[t],j]+=0.5*v*sg
    return H, basis
EOF
cat > test_d2.py << 'EOF'
import numpy as np
from ff import build_V
from fock import hamiltonian
from ff import build_h
import sys
h0=np.zeros((10,10))
for F2,F4 in [(1.0,0.625),(0.5,0.3),(1.0,0.5)]:
    F={0:0.0,2:F2,4:F4}
    V=build_V(F)
    H,b=hamiltonian(2,h0,V)
    ev=np.linalg.eigvalsh(H)
    print(F2,F4,np.round(np.unique(np.round(ev,6)),6))
EOF
time python3 test_d2.py