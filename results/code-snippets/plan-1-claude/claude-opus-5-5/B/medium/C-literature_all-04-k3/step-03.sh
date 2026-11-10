cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2):
    # c^k(l m1, l m2) = sqrt(4pi/(2k+1)) <l m1|Y_k,m1-m2|l m2>
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def two(a,b,c,d,F):
    # <ab|g|cd>, a,c electron1; b,d electron2
    if orbs[a][1]!=orbs[c][1] or orbs[b][1]!=orbs[d][1]: return 0
    ma,mb,mc,md=orbs[a][0],orbs[b][0],orbs[c][0],orbs[d][0]
    if ma+mb!=mc+md: return 0
    return sum(CK[(k,ma,mc)]*CK[(k,md,mb)]*F[k] for k in (2,4))
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def H(Dq,B,C):
    F={2:49*B+7*C,4:12.6*C}
    V=np.zeros((5,5)); 
    for i,m in enumerate(ms): V[i,i]={0:6,1:-4,2:1}[abs(m)]*Dq
    V[0,4]=V[4,0]=5*Dq
    h1=np.zeros((10,10))
    for i,(m,s) in enumerate(orbs):
        for j,(n,t) in enumerate(orbs):
            if s==t: h1[i,j]=V[ms.index(m),ms.index(n)]
    g=np.zeros((10,)*4)
    for a,b,c,d in itertools.product(range(10),repeat=4): g[a,b,c,d]=two(a,b,c,d,F)
    N=len(dets); Hm=np.zeros((N,N))
    # brute force via second quantization
    def apply_ann(det,p):
        if p not in det: return None,0
        i=det.index(p); return tuple(x for x in det if x!=p),(-1)**i
    def apply_cre(det,p):
        if p in det: return None,0
        l=sorted(det+(p,)); i=l.index(p); return tuple(l),(-1)**i
    for J,dj in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if h1[p,q]==0: continue
                d1,s1=apply_ann(dj,q)
                if d1 is None: continue
                d2,s2=apply_cre(d1,p)
                if d2 is None: continue
                Hm[idx[d2],J]+=h1[p,q]*s1*s2
        for p,q,r,s in itertools.product(range(10),repeat=4):
            if g[p,q,r,s]==0: continue
            d1,x1=apply_ann(dj,r)
            if d1 is None: continue
            d2,x2=apply_ann(d1,s)
            if d2 is None: continue
            d3,x3=apply_cre(d2,q)
            if d3 is None: continue
            d4,x4=apply_cre(d3,p)
            if d4 is None: continue
            Hm[idx[d4],J]+=0.5*g[p,q,r,s]*x1*x2*x3*x4
    return Hm
# S^2 to label
def levels(Dq,B,C):
    e=np.linalg.eigvalsh(H(Dq,B,C)); e=e-e[0]
    u=[];  
    for x in e:
        if not u or abs(x-u[-1][0])>1e-3: u.append([x,1])
        else: u[-1][1]+=1
    return u
print(levels(1750,610.9,3000)[:6])
EOF
python3 /tmp/d3.py