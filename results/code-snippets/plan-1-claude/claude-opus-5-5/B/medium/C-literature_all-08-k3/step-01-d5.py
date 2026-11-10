import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
so=[(m,s) for s in (0,1) for m in ms]
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,m1-m2,m2))
C={}
for k in (0,2,4):
  for a in ms:
    for b in ms: C[k,a,b]=ck(k,a,b)
def g(a,b,c,d,F):  # <ab|1/r|cd> orbital m's
    if a+b!=c+d: return 0
    return sum(F[k]*C[k,a,c]*C[k,d,b] for k in (0,2,4))
dets=list(itertools.combinations(range(10),5))
idx={d:i for i,d in enumerate(dets)}
def build(Dq,B,Cc):
    F={0:0,2:49*B+7*Cc,4:441*Cc/35}
    V=np.zeros((5,5))
    for i,m in enumerate(ms):
        V[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    N=len(dets);H=np.zeros((N,N))
    for I,d in enumerate(dets):
        occ=list(d)
        # one-body
        for p in occ:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=V[ms.index(so[q][0]),ms.index(so[p][0])]
                if v==0: continue
                if q!=p and q in occ: continue
                new=[q if x==p else x for x in occ]
                sign=(-1)**sum(1 for x in occ if x!=p and min(p,q)<x<max(p,q))
                srt=tuple(sorted(new));H[idx[srt],I]+=sign*v
        # two-body: sum_{p<q} a_r+ a_s+ a_q a_p
        for p,q in itertools.combinations(occ,2):
            rest=[x for x in occ if x not in (p,q)]
            for r in range(10):
              for s in range(10):
                if r==s or r in rest or s in rest: continue
                if so[r][1]!=so[p][1] or so[s][1]!=so[q][1]: continue
                v=g(so[r][0],so[s][0],so[p][0],so[q][0],F)
                if v==0: continue
                # state a_r+ a_s+ a_q a_p |occ>
                lst=list(occ); sg=1
                for x in (p,q):
                    k=lst.index(x); sg*=(-1)**k; lst.pop(k)
                for x in (s,r):
                    k=sum(1 for y in lst if y<x); sg*=(-1)**k; lst.insert(k,x)
                H[idx[tuple(lst)],I]+=0.5*sg*v*1  # 0.5 since over r,s ordered pairs both directions for p<q? 
        pass
    return H
# Sz=3/2 sector filter
