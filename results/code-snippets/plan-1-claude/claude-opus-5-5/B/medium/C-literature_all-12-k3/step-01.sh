
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ml=[-2,-1,0,1,2]; so=[(m,s) for m in ml for s in (0,1)]
# Slater integrals: F0 irrelevant, F2=49(B... ) use B,C: F2=49B+7C, F4=441C/35 -> standard: F2 = 49B+7C (in F_k with denominators) 
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(5*5)*0+0)
from sympy.physics.wigner import wigner_3j
import functools
@functools.lru_cache(None)
def c(k,m1,m2):
    # c^k(l m1, l m2) for l=2
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
def R(m1,m2,m3,m4,F):  # <m1 m2|1/r|m3 m4>
    if m1+m2!=m3+m4: return 0
    return sum(F[k]*c(k,m1,m3)*c(k,m4,m2) for k in (0,2,4))
# crystal field oct in ml basis (z along C4): V = Dq*(6 on m0, -4 on ±1, 1 on ±2, 5 couple ±2)
V=np.zeros((5,5)); idx={m:i for i,m in enumerate(ml)}
for m,v in zip(ml,[1,-4,6,-4,1]): V[idx[m],idx[m]]=v
V[idx[2],idx[-2]]=V[idx[-2],idx[2]]=5
dets=list(itertools.combinations(range(10),7))
dind={d:i for i,d in enumerate(dets)}
N=len(dets)
def build(Dq,B,C):
    F={0:0,2:49*B+7*C,4:441*C/35}
    H=np.zeros((N,N))
    for i,d in enumerate(dets):
        # one-body
        for p in d:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=Dq*V[idx[so[q][0]],idx[so[p][0]]]
                if v==0: continue
                if q!=p and q in d: continue
                nd=list(d); pos=nd.index(p); sign=(-1)**pos; nd.pop(pos)
                # insert q
                k=sum(1 for x in nd if x<q); sign*=(-1)**k; nd.insert(k,q)
                H[dind[tuple(nd)],i]+=sign*v
        # two-body: sum_{p<q} a+_r a+_s a_q a_p
        for a,b in itertools.combinations(d,2):
            for r in range(10):
                for s in range(10):
                    if r==s: continue
                    if so[r][1]!=so[a][1] or so[s][1]!=so[b][1]: continue
                    v=R(so[r][0],so[s][0],so[a][0],so[b][0],F)
                    if v==0: continue
                    nd=list(d); sign=1
                    pb=nd.index(b); sign*=(-1)**pb; nd.pop(pb)
                    pa=nd.index(a); sign*=(-1)**pa; nd.pop(pa)
                    if s in nd or r in nd: continue
                    k=sum(1 for x in nd if x<s); sign*=(-1)**k; nd.insert(k,s)
                    k=sum(1 for x in nd if x<r); sign*=(-1)**k; nd.insert(k,r)
                    H[dind[tuple(nd)],i]+=sign*v
    return H
Sz=np.array([sum(0.5 if so[p][1] else -0.5 for p in d) for d in dets])
def levels(Dq,B,C):
    H=build(Dq,B,C)
    # restrict to Sz=1/2 and use S^2 via energy degeneracies; easier: compute in Sz=3/2 (quartets) and Sz=1/2
    out={}
    for sz in (1.5,0.5):
        ii=np.where(np.isclose(Sz,sz))[0]
        out[sz]=np.linalg.eigvalsh(H[np.ix_(ii,ii)])
    return out
import sys
L=levels(625,800,3200)
q=L[1.5]; E0=q[0]
print(np.round(q-E0,0))
d=L[0.5]; print(np.round(d-E0,0)[:60])
EOF
python3 /tmp/d7.py
