
cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve
l=2
# ck(m1,m2) coefficients
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*(2*l+1)*gaunt(l,k,l,-m1,m1-m2,m2))
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
def eri(a,b,c,d,F):  # <ab|cd> spin orbitals, phys notation
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=[orbs[i] for i in (a,b,c,d)]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(ck(k,ma,mc)*ck(k,md,mb)*F[k] for k in (0,2,4))
def build(Dq,B,C):
    F={0:0,2:49*B+7*C,4:63*C/5}
    # crystal field in complex basis: Oh
    h=np.zeros((5,5))
    for i,m in enumerate(ms):
        h[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    h[0,4]=h[4,0]=5*Dq
    n=len(dets);H=np.zeros((n,n))
    idx={d:i for i,d in enumerate(dets)}
    for I,D in enumerate(dets):
        for J,E in enumerate(dets):
            diff=set(D)^set(E)
            if len(diff)>4: continue
            # general via second quantization brute force
            pass
    return H
# simpler: brute second quantization
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
def build(Dq,B,C):
    F={0:0,2:49*B+7*C,4:63*C/5}
    h=np.zeros((5,5))
    for i,m in enumerate(ms):
        h[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    h[0,4]=h[4,0]=5*Dq
    idx={d:i for i,d in enumerate(dets)};n=len(dets);H=np.zeros((n,n))
    for J,E in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=h[ms.index(orbs[p][0]),ms.index(orbs[q][0])]
                if v==0: continue
                d,s=apply([('c',p),('a',q)],E)
                if d: H[idx[d],J]+=v*s
        for a in E:
         for b in E:
          for c in range(10):
           for d_ in range(10):
            v=eri(c,d_,a,b,F)
            if v==0: continue
            d,s=apply([('c',c),('c',d_),('a',b),('a',a)],E)
            if d: H[idx[d],J]+=0.5*v*s
    return H
def levels(Dq,B,C):
    w=np.linalg.eigvalsh(build(Dq,B,C));w=w-w[0]
    u=[];c=[]
    for x in w:
        if u and abs(x-u[-1])<1e-3: c[-1]+=1
        else: u.append(x);c.append(1)
    return list(zip(np.round(u,1),c))
def f(p):
    Dq,B,C=p;L=levels(Dq,B,C)
    # degeneracies: 4A2=4, 2E=4, 4T2=12, 4T1=12
    e2E=[x for x,c in L if c==4][1]; t=[x for x,c in L if c==12]
    # 4T2 first 12-fold quartet? 2T1 also 6-fold, 2T2 6-fold
    return [L, e2E]
print(levels(2660,529.4,3001))
EOF
python3 /tmp/d3.py
