python3 - <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq
B=922.;C=4156.
F4=12.6*C;F2=49*B+7*C
ms=range(-2,3)
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,-m1,m1-m2,m2)*wigner_3j(2,k,2,0,0,0))
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
idx={o:i for i,o in enumerate(orbs)}
Fk={2:F2,4:F4}
def gg(m1,m2,m3,m4):
    if m1+m2!=m3+m4: return 0
    return sum(Fk[k]*c(k,m1,m3)*c(k,m4,m2) for k in (2,4))
G={a:gg(*a) for a in itertools.product(ms,repeat=4)}
V={}
for a in orbs:
 for b in orbs:
  for cc in orbs:
   for d in orbs:
    if a[1]==cc[1] and b[1]==d[1]:
     v=G[(a[0],b[0],cc[0],d[0])]
     if v: V[(idx[a],idx[b],idx[cc],idx[d])]=v
def apply(ops,det):
    s=list(det);sign=1
    for (o,cr) in ops:
        if cr:
            if o in s: return None,0
            p=sum(1 for x in s if x<o); sign*=(-1)**p; s.append(o); s.sort()
        else:
            if o not in s: return None,0
            p=sum(1 for x in s if x<o); sign*=(-1)**p; s.remove(o)
    return tuple(s),sign
cache={}
def H(Dq,Ms2):
    dets=[d for d in itertools.combinations(range(10),7) if sum(orbs[i][1] for i in d)==Ms2/2]
    pos={d:i for i,d in enumerate(dets)}
    h=np.zeros((10,10))
    for (m,s) in orbs:
        i=idx[(m,s)]
        h[i,i]={2:1,-2:1,1:-4,-1:-4,0:6}[m]*Dq
        if abs(m)==2: h[i,idx[(-m,s)]]=5*Dq
    if Ms2 not in cache:
        T=[]
        for d in dets:
            j=pos[d]
            for (a,b,cc,dd),v in V.items():
                r,sg=apply([(cc,0),(dd,0),(b,1),(a,1)],d)
                if r is not None: T.append((pos[r],j,0.5*sg*v))
        cache[Ms2]=(dets,pos,T)
    dets,pos,T=cache[Ms2]
    M=np.zeros((len(dets),len(dets)))
    for r,j,v in T: M[r,j]+=v
    for d in dets:
        j=pos[d]
        for p in range(10):
            for q in range(10):
                if h[p,q]:
                    r,sg=apply([(q,0),(p,1)],d)
                    if r is not None: M[pos[r],j]+=sg*h[p,q]
    return np.linalg.eigvalsh((M+M.T)/2)
def f(Dq):
    e3=H(Dq,3); q=e3[0]
    e=H(Dq,1)
    dq=[x for x in e if np.min(abs(e3-x))>1e-6]
    return dq[0]-q
for D in (0,500,1000,1500,2000,2500): print(D,f(D))
print(brentq(f,500,3000,xtol=0.01))
E