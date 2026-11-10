
cd <SANDBOX_TMP>/tmp.dJiUhyh28T && cat << 'EOF' > full.py
import numpy as np
from itertools import combinations
exec(open('d7.py').read().split('pairs=list')[0])
# spin-orbital index: so = 2*orb + s (s=0 up,1 down); orbitals index 0..4 for ms list
nm=10
def cdag_mat(i):
    # Jordan-Wigner on nm modes
    dim=2**nm; M=np.zeros((dim,dim))
    for st in range(dim):
        if not (st>>i)&1:
            sign=(-1)**bin(st&((1<<i)-1)).count('1')
            M[st|(1<<i),st]=sign
    return M
C=[cdag_mat(i) for i in range(nm)]
Cd=C  # creation; annihilation = transpose
Ann=[c.T for c in C]
def so(o,s): return 2*o+s
def build_H(Dq,B,C_):
    F4=12.6*C_; F2=49*B+7*C_
    V=F2*A2+F4*A4   # V[a,b,c,d]=<ab|V|cd> orbital
    h=Dq*h_dq
    dim=2**nm
    H=np.zeros((dim,dim))
    # one-body
    for o1 in range(5):
        for o2 in range(5):
            if abs(h[o1,o2])<1e-12: continue
            for s in (0,1):
                H+= h[o1,o2].real*(C[so(o1,s)]@Ann[so(o2,s)])
    # two-body 1/2 sum V_{ab,cd} c†_a c†_b c_d c_c, spin deltas
    for a in range(5):
     for b in range(5):
      for c in range(5):
       for d in range(5):
        v=V[a,b,c,d].real
        if abs(v)<1e-12: continue
        for s1 in (0,1):
         for s2 in (0,1):
            # <a s1, b s2 | V | c s1, d s2> : electron1 a(s1)<-c(s1), electron2 b(s2)<-d(s2)
            H+=0.5*v*(C[so(a,s1)]@C[so(b,s2)]@Ann[so(d,s2)]@Ann[so(c,s1)])
    return H
# Number-N subspace with 7 electrons, and S^2
Nop=sum(C[i]@Ann[i] for i in range(nm))
Sz=sum(0.5*(C[so(o,0)]@Ann[so(o,0)]-C[so(o,1)]@Ann[so(o,1)]) for o in range(5))
S_plus=sum(C[so(o,0)]@Ann[so(o,1)] for o in range(5))
S2=Sz@Sz+0.5*(S_plus.T@S_plus+S_plus@S_plus.T)
idx=[st for st in range(2**nm) if bin(st).count('1')==7]
def levels(Dq,B,C_):
    H=build_H(Dq,B,C_)
    Hs=H[np.ix_(idx,idx)]
    S2s=S2[np.ix_(idx,idx)]
    # diagonalize H; then label S by expectation
    w,U=np.linalg.eigh(Hs)
    s2=np.einsum('ij,ik,kj->j',U,S2s,U)
    return w,s2
if __name__=="__main__":
    w,s2=levels(1.0,0,0)
    for e,s in zip(w,s2): print(round(e,4),round(s,3))
EOF
python3 full.py 2>&1 | head -130 | awk '{print}' | sort -n | uniq -c | head -40
