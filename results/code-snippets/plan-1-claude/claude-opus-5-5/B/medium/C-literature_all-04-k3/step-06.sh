cd $TMPDIR && cat << 'EOF' > d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
CK={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
dets=list(itertools.combinations(range(10),3)); idx={d:i for i,d in enumerate(dets)}
def ann(det,p):
    if p not in det: return None,0
    i=det.index(p); return tuple(x for x in det if x!=p),(-1)**i
def cre(det,p):
    if p in det: return None,0
    l=sorted(det+(p,)); return tuple(l),(-1)**l.index(p)
def build_two(k):
    g=np.zeros((10,)*4)
    for a,b,c,d in itertools.product(range(10),repeat=4):
        if orbs[a][1]!=orbs[c][1] or orbs[b][1]!=orbs[d][1]: continue
        ma,mb,mc,md=orbs[a][0],orbs[b][0],orbs[c][0],orbs[d][0]
        if ma+mb!=mc+md: continue
        g[a,b,c,d]=CK[(k,ma,mc)]*CK[(k,md,mb)]
    N=len(dets); M=np.zeros((N,N))
    nz=np.argwhere(np.abs(g)>1e-12)
    for J,dj in enumerate(dets):
        for p,q,r,s in nz:
            d1,x1=ann(dj,r)
            if d1 is None: continue
            d2,x2=ann(d1,s)
            if d2 is None: continue
            d3,x3=cre(d2,q)
            if d3 is None: continue
            d4,x4=cre(d3,p)
            if d4 is None: continue
            M[idx[d4],J]+=0.5*g[p,q,r,s]*x1*x2*x3*x4
    return M
def build_one():
    V=np.zeros((5,5))
    for i,m in enumerate(ms): V[i,i]={0:6,1:-4,2:1}[abs(m)]
    V[0,4]=V[4,0]=5
    h1=np.zeros((10,10))
    for i,(m,s) in enumerate(orbs):
        for j,(n,t) in enumerate(orbs):
            if s==t: h1[i,j]=V[ms.index(m),ms.index(n)]
    N=len(dets); M=np.zeros((N,N))
    for J,dj in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if h1[p,q]==0: continue
                d1,s1=ann(dj,q)
                if d1 is None: continue
                d2,s2=cre(d1,p)
                if d2 is None: continue
                M[idx[d2],J]+=h1[p,q]*s1*s2
    return M
H1=build_one(); G2=build_two(2); G4=build_two(4)
def levels(Dq,B,C):
    H=Dq*H1+(49*B+7*C)*G2+12.6*C*G4
    e=np.linalg.eigvalsh(H); e=e-e[0]
    u=[]
    for x in e:
        if not u or abs(x-u[-1][0])>1e-4: u.append([x,1])
        else: u[-1][1]+=1
    return u
print([(round(a,1),b) for a,b in levels(1750,610.9,3000)[:8]])
def f(p):
    Dq,B,C=p; L=levels(Dq,B,C)
    q=[x for x,n in L if n==12]; d=[x for x,n in L if n==4]
    return [q[0]-17500,q[1]-23800,d[0]-14300]
sol=fsolve(f,[1750,610,3000]); print(sol, sol[2]/sol[1])
print([(round(a,1),b) for a,b in levels(*sol)[:8]])
EOF
python3 d3.py