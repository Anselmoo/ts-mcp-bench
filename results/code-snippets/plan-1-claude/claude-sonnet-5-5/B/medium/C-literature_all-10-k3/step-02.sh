
mkdir -p /tmp/w; cd /tmp/w; cat > a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0,1)]
def ckk(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,q,m2))
C={k:np.array([[ckk(k,a,b) for b in ms] for a in ms]) for k in (2,4)}
dets=[d for d in itertools.combinations(range(10),6) if sum(1 for x in d if x%2==0)==3]
idx={d:i for i,d in enumerate(dets)}
def apply(ops,det):
    occ=list(det); sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in occ: return 0,None
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return 0,None
            p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
    return sign,tuple(occ)
# S2 via S-S+ with Ms=1 dets
d1=[d for d in itertools.combinations(range(10),6) if sum(1 for x in d if x%2==0)==4]
i1={d:i for i,d in enumerate(d1)}
Sp=np.zeros((len(d1),len(dets)))
for det in dets:
    for m in range(5):
        s,nd=apply([('c',2*m),('a',2*m+1)],det)
        if s: Sp[i1[nd],idx[det]]+=s
S2=Sp.T@Sp
# precompute terms
one=[];two=[]
for det in dets:
    j=idx[det]
    for p in range(10):
      for q in range(10):
        if so[p][1]!=so[q][1]: continue
        s,nd=apply([('c',p),('a',q)],det)
        if s: one.append((idx[nd],j,so[p][0]+2,so[q][0]+2,s))
    for p in range(10):
     for q in range(10):
      for r in range(10):
       for t in range(10):
        if so[p][1]!=so[r][1] or so[q][1]!=so[t][1]: continue
        if so[p][0]+so[q][0]!=so[r][0]+so[t][0]: continue
        s,nd=apply([('c',p),('c',q),('a',t),('a',r)],det)
        if s: two.append((idx[nd],j,so[p][0]+2,so[q][0]+2,so[r][0]+2,so[t][0]+2,s))
def ham(Dq,B,Cc):
    F={2:49*B+7*Cc,4:1.4*Cc}
    h=np.zeros((5,5))
    for m,v in zip(ms,[Dq,-4*Dq,6*Dq,-4*Dq,Dq]): h[m+2,m+2]=v
    h[0,4]=h[4,0]=5*Dq
    H=np.zeros((len(dets),)*2)
    for a,b,p,q,s in one: H[a,b]+=s*h[p,q]
    for a,b,p,q,r,t,s in two:
        v=sum(C[k][p,r]*C[k][t,q]*F[k] for k in F)
        H[a,b]+=0.5*s*v
    return H
def levels(Dq,B,Cc):
    H=ham(Dq,B,Cc)+1e5*S2
    w=np.linalg.eigvalsh(H); w=w[w<5e4]
    # cluster
    out=[];
    for x in w:
        if out and abs(x-out[-1][0])<1e-3: out[-1][1]+=1
        else: out.append([x,1])
    return out
if __name__=="__main__":
    L=levels(2000,600,2700)
    for x,d in L[:8]: print(x-L[0][0],d)
E
python3 a.py