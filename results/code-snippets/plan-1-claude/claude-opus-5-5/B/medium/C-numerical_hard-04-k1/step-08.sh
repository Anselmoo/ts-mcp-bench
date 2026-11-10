mkdir -p <SANDBOX_TMP>/m7s1 && cd <SANDBOX_TMP>/m7s1 && cat > d5.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2): return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
n=10
dets=list(itertools.combinations(range(n),5))
idx={d:i for i,d in enumerate(dets)}
def ann(L,q):
    if L is None or q not in L: return None,0
    k=L.index(q); return L[:k]+L[k+1:],(-1)**k
def cre(L,p):
    if L is None or p in L: return None,0
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
HD=np.zeros((N,N)); HF={2:np.zeros((N,N)),4:np.zeros((N,N))}; S2=np.zeros((N,N))
for i,D in enumerate(dets):
    D=list(D)
    for p in range(n):
        for q in range(n):
            if orbs[p][1]!=orbs[q][1]: continue
            v=h1(orbs[p][0],orbs[q][0])
            if not v: continue
            L,s1=ann(D,q); L,s2=cre(L,p)
            if L is None: continue
            HD[idx[tuple(L)],i]+=v*s1*s2
    for r in D:
        for s in D:
            if r==s: continue
            L,s1=ann(D,r); L,s2=ann(L,s)
            for p in range(n):
                for q in range(n):
                    if p==q: continue
                    M,s3=cre(L,q); M,s4=cre(M,p)
                    if M is None: continue
                    for k in (2,4):
                        v=eri(p,q,r,s,k)
                        if v: HF[k][idx[tuple(M)],i]+=0.5*v*s1*s2*s3*s4
    na=sum(1 for x in D if orbs[x][1]==0); sz=(na-(5-na))/2
    S2[i,i]+=sz*sz
    for (u,dn) in [(0,1),(1,0)]:
        for a in range(5):
            for b in range(5):
                L,s1=ann(D,2*a+dn); L,s2=cre(L,2*a+u); L,s3=ann(L,2*b+u); L,s4=cre(L,2*b+dn)
                if L is None: continue
                S2[idx[tuple(L)],i]+=0.5*s1*s2*s3*s4
np.savez('m.npz',HD=HD,F2=HF[2],F4=HF[4],S2=S2)
EOF
python3 d5.py && cat > fit.py << 'EOF'
import numpy as np
from scipy.optimize import least_squares
z=np.load('m.npz');HD,F2,F4,S2=z['HD'],z['F2'],z['F4'],z['S2']
def levels(Dq,B,C):
    H=Dq*HD+(49*B+7*C)*F2+(441*C/35)*F4
    w,v=np.linalg.eigh(H+1e-4*S2)
    s=np.einsum('ji,jk,ki->i',v,S2,v)
    S=np.round(-1+np.sqrt(1+4*s))/2
    return w-w[0],S
e,S=levels(0,1000,4000)
print(sorted(set(zip(np.round(e,0),S)))[:5])
def dbl(Dq,B,C=None):
    e,S=levels(Dq,B,4.4*B if C is None else C)
    vals=np.round(e[S==0.5],2); u=np.unique(vals); return S[0],u
print(dbl(3000,600))
EOF
python3 fit.py