
python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
l=2
from functools import lru_cache
@lru_cache(None)
def ck(k,m1,m2):
    if abs(m1-m2)>k: return 0.0
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*(2*l+1)*gaunt(l,k,l,-m1,m1-m2,m2))
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
def apply(ops,det):
    det=list(det);sign=1
    for typ,p in reversed(ops):
        if typ=='a':
            if p not in det: return None,0
            k=det.index(p);sign*=(-1)**k;det.pop(k)
        else:
            if p in det: return None,0
            k=sum(1 for q in det if q<p);sign*=(-1)**k;det.insert(k,p)
    return tuple(det),sign
idx={d:i for i,d in enumerate(dets)};n=len(dets)
def mats():
    Hcf=np.zeros((n,n));HF={2:np.zeros((n,n)),4:np.zeros((n,n))}
    h=np.zeros((5,5))
    for i,m in enumerate(ms): h[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]
    h[0,4]=h[4,0]=5
    for J,E in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=h[ms.index(orbs[p][0]),ms.index(orbs[q][0])]
                if v==0: continue
                d,s=apply([('c',p),('a',q)],E)
                if d: Hcf[idx[d],J]+=v*s
        for a in E:
         for b in E:
          for c in range(10):
           for d_ in range(10):
            (ma,sa),(mb,sb),(mc,sc),(md,sd)=[orbs[i] for i in (c,d_,a,b)]
            if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
            d,s=apply([('c',c),('c',d_),('a',b),('a',a)],E)
            if not d: continue
            for k in (2,4):
                HF[k][idx[d],J]+=0.5*s*ck(k,ma,mc)*ck(k,md,mb)
    return Hcf,HF
Hcf,HF=mats()
def levels(Dq,B,C):
    H=Dq*Hcf+(49*B+7*C)*HF[2]+(63*C/5)*HF[4]
    w=np.linalg.eigvalsh(H);w=w-w[0]
    u=[];c=[]
    for x in w:
        if u and abs(x-u[-1])<1e-2: c[-1]+=1
        else: u.append(x);c.append(1)
    return list(zip(np.round(u,1),c))
print(levels(2660,529.4,3001)[:6])
# solve: 4T2 & 4T1 depend only on Dq,B; 2E via C
def get(Dq,B,C):
    L=levels(Dq,B,C)
    return L
from scipy.optimize import fsolve
def res(p):
    Dq,B,C=p
    H=Dq*Hcf+(49*B+7*C)*HF[2]+(63*C/5)*HF[4]
    w=np.linalg.eigvalsh(H);w=w-w[0]
    # identify: first 4 = 4A2; 2E is 4-fold next; need labeled. use spin: compute via S^2? simple: order
    L=levels(Dq,B,C)
    q=[x for x,c in L if c==12]  # 4T2,4T1 (2T multiplets are 6-fold)
    e=[x for x,c in L if c==4][1]
    return [q[0]-26600,q[1]-32500,e-12820]
s=fsolve(res,[2660,529,3001]);print(s,levels(*s)[:8])
EOF
