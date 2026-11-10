
cat << 'EOF' > /tmp/d5.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
l=2; ms=range(-2,3)
# ck coefficients
def ck(k,m1,m2): return float((-1)**m1*np.sqrt(25)*np.sqrt(1)* 0) 
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
orbs=[(m,s) for m in ms for s in (0,1)]
n=10
# two-electron integral <ab|cd> = sum_k R^k c^k(ma,mc) c^k(md,mb) delta(ma+mb,mc+md) spins
def eri(a,b,cc,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[cc],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
    return sum(F[k]*c(k,ma,mc)*c(k,md,mb) for k in (0,2,4))
dets=list(itertools.combinations(range(n),5))
idx={d:i for i,d in enumerate(dets)}
# one-electron: octahedral crystal field in real-m basis: V = Dq*(6 for m=0? ) use complex m: <m|V|m'>
# Oh: diag m=0:6Dq, m=±1:-4Dq, m=±2: Dq; offdiag <2|V|-2>=5Dq
def h1(m,mp):
    if m==mp: return {0:6,1:-4,-1:-4,2:1,-2:1}[m]
    if abs(m-mp)==4: return 5
    return 0
def build(Dq,B,C):
    F={0:0.,2:49*B+7*C,4:441*C/35}
    # check: B=(F2-5F4/... ) standard: F2=49B+7C? F^2 (unnormalized)=49F2,F2=B+C/7 ->F^2=49B+7C ; F4=C/35 ->F^4=441*C/35
    N=len(dets);H=np.zeros((N,N))
    for i,D in enumerate(dets):
        for p in range(n):
          for q in range(n):
            if orbs[p][1]!=orbs[q][1]: continue
            v=h1(orbs[p][0],orbs[q][0])*Dq
            if v==0: continue
            if q not in D: continue
            L=list(D); sgn=(-1)**L.index(q); L.remove(q)
            if p in L: continue
            L.append(p); # sort sign
            perm=np.argsort(L); s2=np.linalg.det(np.eye(5)[perm])
            H[idx[tuple(sorted(L))],i]+=v*sgn*(-1)**sum(1 for x in L[:-1] if x>p)
        # two-electron: a+b+ d c
        for q1,q2 in itertools.combinations(D,2):
          for p1 in range(n):
            for p2 in range(p1+1,n):
              L=list(D)
              sg=1
              # annihilate q2 then q1 (operator a_p1+ a_p2+ a_q2 a_q1)
              k=L.index(q1); sg*=(-1)**k; L.pop(k)
              k=L.index(q2); sg*=(-1)**k; L.pop(k)
              if p1 in L or p2 in L: continue
              # create p2 then p1
              k=sum(1 for x in L if x<p2); sg*=(-1)**k; L.insert(k,p2)
              k=sum(1 for x in L if x<p1); sg*=(-1)**k; L.insert(k,p1)
              v=eri(p1,p2,q1,q2,F)-eri(p1,p2,q2,q1,F)
              if v: H[idx[tuple(L)],i]+=sg*v
    return H
import pickle
# precompute parts linearly
H_D=build(1,0,0);H_B=build(0,1,0);H_C=build(0,0,1)
# S^2 for spin labelling: use Sz=1/2 subset and S^2
def S2():
    N=len(dets);S=np.zeros((N,N))
    for i,D in enumerate(dets):
        na=sum(1 for x in D if orbs[x][1]==0); nb=5-na
        sz=(na-nb)/2; S[i,i]+=sz*sz-sz  # S2=S-S+ + Sz^2+Sz ; use S+S- + Sz^2 - Sz
        # S+S-: lower then raise
        for q in D:
            if orbs[q][1]!=0: continue
            pd=q+1 # beta partner
            if pd in D: continue
            L=list(D);k=L.index(q);sg=(-1)**k;L.pop(k)
            k2=sum(1 for x in L if x<pd);sg*=(-1)**k2;L.insert(k2,pd)
            for q2 in L:
                if orbs[q2][1]!=1: continue
                pu=q2-1
                if pu in L: continue
                M=list(L);k=M.index(q2);s3=sg*(-1)**k;M.pop(k)
                k2=sum(1 for x in M if x<pu);s3*=(-1)**k2;M.insert(k2,pu)
                S[idx[tuple(M)],i]+=s3
    return S
S=S2()
np.save('/tmp/H.npy',np.array([H_D,H_B,H_C,S]))
EOF
python3 /tmp/d5.py && echo ok
