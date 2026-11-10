cd /dev/shm && cat << 'EOF' > d5.py
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
def c(k,m1,m2): return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
n=10
dets=list(itertools.combinations(range(n),5))
idx={d:i for i,d in enumerate(dets)}
def ann(L,q):
    if q not in L: return None,0
    k=L.index(q); return L[:k]+L[k+1:],(-1)**k
def cre(L,p):
    if p in L: return None,0
    k=sum(1 for x in L if x<p); return L[:k]+[p]+L[k:],(-1)**k
cache={}
def cc(k,a,b):
    if (k,a,b) not in cache: cache[(k,a,b)]=c(k,a,b)
    return cache[(k,a,b)]
def eri(a,b,C_,d,k):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[C_],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
    return cc(k,ma,mc)*cc(k,md,mb)
def h1(m,mp):
    if m==mp: return {0:6,1:-4,-1:-4,2:1,-2:1}[m]
    if abs(m-mp)==4: return 5
    return 0
N=len(dets)
HD=np.zeros((N,N)); HF={0:np.zeros((N,N)),2:np.zeros((N,N)),4:np.zeros((N,N))}; S2=np.zeros((N,N))
for i,D in enumerate(dets):
    D=list(D)
    for p in range(n):
        for q in range(n):
            if orbs[p][1]!=orbs[q][1]: continue
            v=h1(orbs[p][0],orbs[q][0])
            if not v: continue
            L,s1=ann(D,q)
            if L is None: continue
            L,s2=cre(L,p)
            if L is None: continue
            HD[idx[tuple(L)],i]+=v*s1*s2
    # 0.5 sum <pq|rs> a+p a+q a s a r
    for r in D:
        for s in D:
            if r==s: continue
            L,s1=ann(D,r); L,s2=ann(L,s)
            for p in range(n):
                for q in range(n):
                    if p==q: continue
                    M,s3=cre(L,q)
                    if M is None: continue
                    M,s4=cre(M,p)
                    if M is None: continue
                    for k in (0,2,4):
                        v=eri(p,q,r,s,k)
                        if v: HF[k][idx[tuple(M)],i]+=0.5*v*s1*s2*s3*s4
    # S2 = Sz^2 + (S+S- + S-S+)/2 ; S+ = sum a+_{m,0} a_{m,1}
    na=sum(1 for x in D if orbs[x][1]==0); sz=(na-(5-na))/2
    S2[i,i]+=sz*sz
    for (u,dn) in [(0,1),(1,0)]:
        for a in range(5):
            for b in range(5):
                q1=2*a+dn; p1=2*a+u; q2=2*b+u; p2=2*b+dn
                # (S_x S_y terms) operator a+p2 a q2 then a+p1 a q1 : S(opp) S
                L,s1=ann(D,q1)
                if L is None: continue
                L,s2=cre(L,p1)
                if L is None: continue
                L,s3=ann(L,q2)
                if L is None: continue
                L,s4=cre(L,p2)
                if L is None: continue
                S2[idx[tuple(L)],i]+=0.5*s1*s2*s3*s4
np.save('m.npy',np.array([HD,HF[0],HF[2],HF[4],S2]))
print(np.allclose(HD,HD.T),np.allclose(HF[2],HF[2].T),np.allclose(S2,S2.T))
EOF
python3 d5.py