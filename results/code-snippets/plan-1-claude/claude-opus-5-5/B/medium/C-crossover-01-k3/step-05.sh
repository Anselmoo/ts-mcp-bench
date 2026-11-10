
python3 << 'EOF' 2>&1 | tail -20
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=706.,2734.
F={0:0.,2:49*B+7*C,4:63*C/5}
ml=[-2,-1,0,1,2]
from functools import lru_cache
@lru_cache(None)
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
@lru_cache(None)
def U(a,b,c,d):
    if a+b!=c+d: return 0.
    return sum(F[k]*ck(k,a,c)*ck(k,d,b) for k in (0,2,4))
so=[(m,s) for s in (1,-1) for m in ml]
def V(Dq):
    v=np.zeros((5,5)); i={m:j for j,m in enumerate(ml)}
    v[i[0],i[0]]=6*Dq; v[i[1],i[1]]=v[i[-1],i[-1]]=-4*Dq
    v[i[2],i[2]]=v[i[-2],i[-2]]=Dq; v[i[2],i[-2]]=v[i[-2],i[2]]=5*Dq
    return v
print(np.linalg.eigvalsh(V(1)))
def apply(ops,det):
    det=list(det); sign=1
    for op,o in reversed(ops):
        if op=='a':
            if o not in det: return None,0
            k=det.index(o); sign*=(-1)**k; det.pop(k)
        else:
            if o in det: return None,0
            det=sorted(det+[o]); k=det.index(o); sign*=(-1)**k
    return tuple(det),sign
def build(Ms2):
    dets=[d for d in itertools.combinations(range(10),4) if sum(so[x][1] for x in d)==Ms2]
    idx={d:i for i,d in enumerate(dets)}; n=len(dets)
    hc=np.zeros((n,n)); v=V(1.0); hcf=np.zeros((n,n))
    for d in dets:
        j=idx[d]
        for p in range(10):
            for q in d:
                if so[p][1]!=so[q][1]: continue
                val=v[ml.index(so[p][0]),ml.index(so[q][0])]
                if val==0: continue
                nd,s=apply([('c',p),('a',q)],d)
                if nd: hcf[idx[nd],j]+=s*val
        for r,s_ in itertools.permutations(d,2):
            for p in range(10):
                for q in range(10):
                    if p==q or so[p][1]!=so[r][1] or so[q][1]!=so[s_][1]: continue
                    val=U(so[p][0],so[q][0],so[r][0],so[s_][0])
                    if val==0: continue
                    nd,sg=apply([('c',p),('c',q),('a',s_),('a',r)],d)
                    if nd: hcf_ = 0; hc[idx[nd],j]+=0.5*sg*val
    return hc,hcf
A=build(4); Bm=build(2)
print(np.linalg.eigvalsh(A[1])[:5], np.linalg.eigvalsh(Bm[1])[:5])
f=lambda Dq: np.linalg.eigvalsh(Bm[0]+Dq*Bm[1])[0]-np.linalg.eigvalsh(A[0]+Dq*A[1])[0]
for D in range(0,5000,250): print(D,f(D))
EOF
