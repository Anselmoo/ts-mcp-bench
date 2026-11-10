cat << 'EOF' | python3 -
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
l=2
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]  # index p
n=10
cache={}
def c(k,m,mp,q):
    if m-mp!=q: return 0.0
    key=(k,m,mp,q)
    if key not in cache:
        cache[key]=float((-1)**(l-m)*np.sqrt(2*l+1)*float(wigner_3j(l,k,l,-m,q,mp)))
    return cache[key]
def V2(m1,m2,m3,m4,F2,F4):
    Fk={2:F2,4:F4}
    tot=0.0
    for k,F in Fk.items():
        for q in range(-k,k+1):
            tot+=F*c(k,m1,m3,q)*c(k,m2,m4,-q)*(-1)**q
    return tot
# basis: 8-electron determinants = choose 8 of 10 spin-orbitals -> equivalently 2 holes
states=[s for s in itertools.combinations(range(n),8)]
idx={s:i for i,s in enumerate(states)}
def mm(p): return orbs[p][0]
def sp(p): return orbs[p][1]
# one-electron cubic matrix (5x5) in m basis, Dq units
Mcf=np.zeros((5,5))
# order m=-2..2 -> index 0..4
Mcf[2,2]=-4; Mcf[1,1]=-4; Mcf[3,3]=-4
Mcf[0,0]=1; Mcf[4,4]=1; Mcf[0,4]=5; Mcf[4,0]=5
Mcf[2,2]=6  # m=0 is index 2 ; fix below
# m index: m=-2->0, -1->1, 0->2, 1->3, 2->4
Mcf=np.zeros((5,5))
Mcf[1,1]=Mcf[3,3]=-4
Mcf[2,2]=6
Mcf[0,0]=Mcf[4,4]=1; Mcf[0,4]=Mcf[4,0]=5
def build(Dq,B,C):
    F4=12.6*C; F2=49*B+7*C
    h=np.zeros((n,n))
    for p in range(n):
        for q in range(n):
            if sp(p)==sp(q):
                h[p,q]=Dq*Mcf[mm(p)+2,mm(q)+2]
    # two-electron antisymmetrized  <pq||rs>
    Vt=np.zeros((n,n,n,n))
    for p,q,r,s in itertools.product(range(n),repeat=4):
        if sp(p)==sp(r) and sp(q)==sp(s):
            Vt[p,q,r,s]+=V2(mm(p),mm(q),mm(r),mm(s),F2,F4)
    # H = sum h c+p cq + 1/2 sum V_pqrs c+p c+q c_s c_r  (V_pqrs=<pq|1/r|rs>)
    # build via Fock: use operator matrices in full 2^10 space restricted to N=8
    Hs=np.zeros((len(states),len(states)))
    for i,st in enumerate(states):
        occ=set(st)
        # one-body
        for p in range(n):
            for q in range(n):
                if h[p,q]==0: continue
                # c+p c_q |st>
                if q not in occ: continue
                occ2=set(occ); occ2.remove(q)
                sign=(-1)**sum(1 for x in st if x<q)
                if p in occ2: continue
                sign2=(-1)**sum(1 for x in occ2 if x<p)
                occ2.add(p)
                j=idx[tuple(sorted(occ2))]
                Hs[j,i]+=h[p,q]*sign*sign2
        # two-body: 1/2 sum V_pqrs c+p c+q c_s c_r
        for r in occ:
            for s in occ:
                if r==s: continue
                for p in range(n):
                    for q in range(n):
                        v=Vt[p,q,r,s]
                        if v==0: continue
                        occ2=set(occ); 
                        # apply c_r then c_s? operator c_s c_r acting: first c_r then c_s
                        sg=(-1)**sum(1 for x in occ2 if x<r); occ2.remove(r)
                        sg*=(-1)**sum(1 for x in occ2 if x<s); occ2.remove(s)
                        if p in occ2 or q in occ2 or p==q: continue
                        sg*=(-1)**sum(1 for x in occ2 if x<q); occ2.add(q)
                        sg*=(-1)**sum(1 for x in occ2 if x<p); occ2.add(p)
                        j=idx[tuple(sorted(occ2))]
                        Hs[j,i]+=0.5*v*sg
    return Hs
def S2op():
    # total S^2 on N=8 space: use Sz and S+ S-
    # S+ = sum_m c+_{m,up} c_{m,dn}
    Sz=np.zeros(len(states)); 
    Sp=np.zeros((len(states),len(states)))
    for i,st in enumerate(states):
        occ=set(st)
        Sz[i]=0.5*(sum(1 for x in occ if sp(x)==0)-sum(1 for x in occ if sp(x)==1))
        for m in range(-2,3):
            pu=orbs.index((m,0)); pd=orbs.index((m,1))
            if pd in occ and pu not in occ:
                o2=set(occ); sg=(-1)**sum(1 for x in occ if x<pd); o2.remove(pd)
                sg*=(-1)**sum(1 for x in o2 if x<pu); o2.add(pu)
                Sp[idx[tuple(sorted(o2))],i]+=sg
    Sm=Sp.T
    return Sm@Sp+np.diag(Sz)+np.diag(Sz)**2 - 0  # S^2 = S-S+ + Sz^2 + Sz
def S2(Sp_mat):
    pass
EOF
echo written