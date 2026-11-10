cat > /tmp/tsbench-run-hvexjx5r/d5.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import sqrt, pi
from scipy.optimize import fsolve

l=2
ms=list(range(-2,3))
orbs=[(m,s) for m in ms for s in (+1,-1)]
N=len(orbs)
basis=[sum(1<<i for i in occ) for occ in itertools.combinations(range(N),5)]
idx={b:i for i,b in enumerate(basis)}
D=len(basis)
def gnt(l1,l2,l3,m1,m2,m3):
    return float(gaunt(l1,l2,l3,m1,m2,m3))
W=np.zeros((5,5))
for i,m in enumerate(ms):
    for j,mp in enumerate(ms):
        val=0.0
        for q,a in ((0,1.0),(4,sqrt(5/14)),(-4,sqrt(5/14))):
            if (-m+q)!=mp: continue
            val+= a*((-1)**m)*gnt(2,4,2,-m,q,mp)
        W[i,j]=val
ev,U=np.linalg.eigh(W)
low=ev[:3]; high=ev[3:]
scale=-4.0/np.mean(low)
assert abs(scale-6.0/np.mean(high))<1e-8
Wn=W*scale
def Cmat(k,q):
    M=np.zeros((5,5))
    for i,m in enumerate(ms):
        for j,mp in enumerate(ms):
            if (-m+q)!=mp: continue
            M[i,j]=((-1)**m)*sqrt(4*pi/(2*k+1))*gnt(l,k,l,-m,q,mp)
    return M
Cq={(k,q):Cmat(k,q) for k in (0,2,4) for q in range(-k,k+1)}
Ang={}
for k in (0,2,4):
    T=np.zeros((5,5,5,5))
    for q in range(-k,k+1):
        T+=((-1)**q)*np.einsum('ac,bd->abcd',Cq[(k,-q)],Cq[(k,q)])
    Ang[k]=T
Vk={k:np.zeros((N,N,N,N)) for k in (0,2,4)}
for A,(m1,s1) in enumerate(orbs):
 for B_,(m2,s2) in enumerate(orbs):
  for C_,(m3,s3) in enumerate(orbs):
   for D_,(m4,s4) in enumerate(orbs):
    if s1==s3 and s2==s4:
        i1,i2,i3,i4=ms.index(m1),ms.index(m2),ms.index(m3),ms.index(m4)
        for k in (0,2,4):
            Vk[k][A,B_,C_,D_]=Ang[k][i1,i2,i3,i4]
H1=np.zeros((N,N))
for A,(m1,s1) in enumerate(orbs):
    for B_,(m2,s2) in enumerate(orbs):
        if s1==s2: H1[A,B_]=Wn[ms.index(m1),ms.index(m2)]
def apply_c(p,q,state,dag):
    # apply c^dag_p (dag=True) or c_p to state; return (sign,new) or None
    if dag:
        if (state>>p)&1: return None
    else:
        if not (state>>p)&1: return None
    below=bin(state&((1<<p)-1)).count('1')
    return (-1)**below, state ^ (1<<p)
def one_body(M):
    H=np.zeros((D,D))
    for j,b in enumerate(basis):
        for p in range(N):
            for q in range(N):
                if M[p,q]==0: continue
                r=apply_c(q,0,b,False) if False else None
                # c^dag_p c_q
                r1=apply_c(q,0,b,False)
                if r1 is None: continue
                s1,b1=r1
                r2=apply_c(p,0,b1,True)
                if r2 is None: continue
                s2,b2=r2
                H[idx[b2],j]+=s1*s2*M[p,q]
    return H
def two_body(V):
    H=np.zeros((D,D))
    nz=[(a,b,c,d,V[a,b,c,d]) for a in range(N) for b in range(N) for c in range(N) for d in range(N) if abs(V[a,b,c,d])>1e-12]
    for j,bst in enumerate(basis):
        for (a,b,c,d,v) in nz:
            r=apply_c(c,0,bst,False)
            if r is None: continue
            s1,x=r
            r=apply_c(d,0,x,False)
            if r is None: continue
            s2,x=r
            r=apply_c(b,0,x,True)
            if r is None: continue
            s3,x=r
            r=apply_c(a,0,x,True)
            if r is None: continue
            s4,x=r
            H[idx[x],j]+=0.5*s1*s2*s3*s4*v
    return H
H1m=one_body(H1)
Vm={k:two_body(Vk[k]) for k in (0,2,4)}
Sz=np.diag([sum(0.5*s for i,(m,s) in enumerate(orbs) if (b>>i)&1) for b in basis])
Splus=np.zeros((D,D))
for i,(m,s) in enumerate(orbs):
    if s!=1: continue
    j=orbs.index((m,-1))
    M=np.zeros((N,N)); M[i,j]=1.0
    Splus+=one_body(M)
S2=Splus.T@Splus+Sz@Sz-Sz  # S^2 = S- S+ + Sz^2 + Sz ; S+^T = S- for real matrices
# recompute properly: S- S+ = (S+)^T S+ ; S^2 = S-S+ + Sz^2 + Sz... S^2 = S- S+ + Sz(Sz+1)
S2=Splus.T@Splus+Sz@(Sz+np.eye(D))
# Hamiltonian in units: H = Dq*H1m + F0*(...) + F2*V2 + F4*V4 ; F's from Racah B,C
def H_of(Dq,B,C):
    F4=441*C/35.0
    F2=(441*B+5*F4)/9.0
    return Dq*H1m + F2*Vm[2] + F4*Vm[4]
# Check Racah relations on free ion: F0 contributes const; ignore
# Spectrum split by spin
def levels(Dq,B,C):
    H=H_of(Dq,B,C)
    w,v=np.linalg.eigh(H)
    # spin projection
    s2=np.einsum('ij,jk,ki->i',v.T,S2,v)
    return w,s2
if __name__=="__main__":
    # free-ion check (Dq=0): sextet and quartet energies
    for B,C in [(1000.0,4000.0)]:
        w,s2=levels(0.0,B,C)
        q=sorted(set(np.round(w[np.abs(s2-15/4)<1e-6],3)))
        s=sorted(set(np.round(w[np.abs(s2-35/4)<1e-6],3)))
        print("sextet",s); print("quartet",q)
        print("expected 4G-6S =17B+5C =",17*B+5*C, " 4P=",22*B+5*C)
EOF
cd /tmp/tsbench-run-hvexjx5r && python3 d5.py