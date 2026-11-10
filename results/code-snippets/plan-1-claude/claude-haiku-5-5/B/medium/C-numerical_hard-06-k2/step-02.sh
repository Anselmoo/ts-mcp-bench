mkdir -p /w && cat > /w/ts.py <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from functools import lru_cache
l=2
ms=[-2,-1,0,1,2]
@lru_cache(None)
def w3(a,b,c,d,e,f): return float(wigner_3j(a,b,c,d,e,f))
def ang(k,m,q,mp):
    if m+ -q - mp !=0 and False: pass
    if -m+q+mp!=0 and False: pass
    if abs(q)>k or abs(m)>l or abs(mp)>l: return 0.0
    return (-1)**(l-m)*w3(l,k,l,-m,q,mp)*(-1)**l*(2*l+1)*w3(l,k,l,0,0,0)
def g(k,m1,m2,m3,m4):
    s=0.0
    for q in range(-k,k+1):
        if m1-(-q)!=m3 and False: pass
        s+=(-1)**q*ang(k,m1,-q,m3)*ang(k,m2,q,m4)
    return s
def Vspat(F):
    # V[a,b,c,d] = <ab|g|cd> in orbital indices 0..4 (m=-2..2)
    V=np.zeros((5,5,5,5))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        m1,m2,m3,m4=ms[a],ms[b],ms[c],ms[d]
        if m1+m2!=m3+m4: continue
        val=0
        for k,Fk in ((2,F[2]),(4,F[4])):
            val+=Fk*g(k,m1,m2,m3,m4)
        V[a,b,c,d]=val
    return V
def hspat(Dq):
    h=np.zeros((5,5))
    idx={m:i for i,m in enumerate(ms)}
    # eg: |0>, (|2>+|-2>)/sqrt2 ; t2g: |1>,|-1>, (|2>-|-2>)/sqrt2
    v=np.zeros(5); v[idx[2]]=1/np.sqrt(2); v[idx[-2]]=1/np.sqrt(2)
    u=np.zeros(5); u[idx[2]]=1/np.sqrt(2); u[idx[-2]]=-1/np.sqrt(2)
    e0=np.zeros(5); e0[idx[0]]=1
    e1=np.zeros(5); e1[idx[1]]=1
    em1=np.zeros(5); em1[idx[-1]]=1
    Peg=np.outer(e0,e0)+np.outer(v,v)
    Pt2g=np.outer(e1,e1)+np.outer(em1,em1)+np.outer(u,u)
    return -4*Dq*Pt2g+6*Dq*Peg
# Fock space: 10 spin-orbitals, index = 2*orb+s
states=[sum(1<<i for i in c) for c in itertools.combinations(range(10),6)]
sidx={s:i for i,s in enumerate(states)}
def build(Dq,B,C):
    F={2:49*B+5*C,4:9*C}
    V=Vspat(F); h=hspat(Dq)
    N=len(states); H=np.zeros((N,N))
    # one-electron
    # two-electron: H2 = 1/2 sum V[a,b,c,d] c+_a c+_b c_d c_c (spatial labels with spin conservation)
    so=[(i//2, i%2) for i in range(10)]
    def apply_ops(st, ops):
        # ops: list of (index, dagger) applied right to left; returns (sign, newstate) or None
        s=st; sign=1
        for (i,dag) in ops:
            occ=(s>>i)&1
            if dag and occ: return None
            if (not dag) and (not occ): return None
            # sign = (-1)^{number of occupied orbitals below i}
            nbelow=bin(s & ((1<<i)-1)).count('1')
            if nbelow%2: sign=-sign
            s ^= (1<<i)
        return sign,s
    for col,st in enumerate(states):
        # one-body
        for i in range(10):
            for j in range(10):
                if so[i][1]!=so[j][1]: continue
                hv=h[so[i][0],so[j][0]]
                if abs(hv)<1e-14: continue
                r=apply_ops(st,[(i,True),(j,False)])
                if r is None: continue
                sg,ns=r
                H[sidx[ns],col]+=sg*hv
        # two-body: 1/2 sum V_{abcd} c+_a c+_b c_d c_c with spatial <ab|cd>
        for a in range(10):
            for b in range(10):
                if a==b: continue
                for c in range(10):
                    for d in range(10):
                        if c==d: continue
                        A,Bo,Cc,Dd=so[a][0],so[b][0],so[c][0],so[d][0]
                        if so[a][1]!=so[c][1] or so[b][1]!=so[d][1]: continue
                        v=V[A,Bo,Cc,Dd]
                        if abs(v)<1e-14: continue
                        r=apply_ops(st,[(a,True),(b,True),(d,False),(c,False)])
                        if r is None: continue
                        sg,ns=r
                        H[sidx[ns],col]+=0.5*sg*v
    return H
def Smeasure():
    # total S^2 via S_z and S+S-
    pass
if __name__=="__main__":
    H=build(0,1.0,0.0)
    w=np.linalg.eigvalsh(H)
    vals,counts=np.unique(np.round(w,6),return_counts=True)
    print(list(zip(vals,counts)))
EOF
cd /w && time python3 ts.py