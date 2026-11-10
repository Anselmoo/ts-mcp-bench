import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq
B=803.;C=3078.
F4=63*C/5;F2=(441*B+5*F4)/9
F={0:0,2:F2,4:F4}
def c(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.
    return float(5*(-1)**m*wigner_3j(2,k,2,-m,q,mp)*wigner_3j(2,k,2,0,0,0))
ms=[-2,-1,0,1,2]
cc={(k,a,b):c(k,a,b) for k in (2,4) for a in ms for b in ms}
def g(a,b,cn,d):
    if a+b!=cn+d: return 0.
    return sum(cc[(k,a,cn)]*cc[(k,d,b)]*F[k] for k in (2,4))
so=[(m,s) for m in ms for s in (0,1)]
n=10
V={}
for p in range(n):
 for q in range(n):
  for r in range(n):
   for s in range(n):
    if p==q or r==s: continue
    if so[p][1]!=so[r][1] or so[q][1]!=so[s][1]: continue
    v=g(so[p][0],so[q][0],so[r][0],so[s][0])
    if v!=0: V[(p,q,r,s)]=v
def app(op,det):
    d=list(det);sg=1
    for cr,i in reversed(op):
        if cr:
            if i in d: return None,0
            pos=sum(1 for x in d if x<i); sg*=(-1)**pos; d.append(i); d.sort()
        else:
            if i not in d: return None,0
            pos=d.index(i); sg*=(-1)**pos; d.remove(i)
    return tuple(d),sg
def build(Ms2,Dq):
    dets=[d for d in itertools.combinations(range(n),6) if sum(1 if so[i][1]==0 else -1 for i in d)==Ms2]
    idx={d:i for i,d in enumerate(dets)}
    H=np.zeros((len(dets),)*2)
    h=np.zeros((n,n))
    cf={0:6,1:-4,-1:-4,2:1,-2:1}
    for i,(m,s) in enumerate(so):
        h[i,i]=cf[m]*Dq
        if abs(m)==2: h[i,so.index((-m,s))]=5*Dq
    for d in dets:
        j=idx[d]
        for p in range(n):
            for r in range(n):
                if h[p,r]!=0:
                    nd,sg=app([(1,p),(0,r)],d)
                    if nd: H[idx[nd],j]+=h[p,r]*sg
        for (p,q,r,s),v in V.items():
            nd,sg=app([(1,p),(1,q),(0,s),(0,r)],d)
            if nd: H[idx[nd],j]+=0.5*v*sg
    return H
def gap(Dq):
    return np.linalg.eigvalsh(build(0,Dq))[0]-np.linalg.eigvalsh(build(4,Dq))[0]
for D in (1000,1500,2000,2500): print(D,gap(D))
print(brentq(gap,1000,3000,xtol=0.01))
