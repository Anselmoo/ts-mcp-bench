import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,m1-m2,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def coul(a,b,c,d,F):  # <ab|1/r|cd>
    if a[1]!=c[1] or b[1]!=d[1]: return 0
    if a[0]+b[0]!=c[0]+d[0]: return 0
    return sum(F[k]*C[(k,a[0],c[0])]*C[(k,d[0],b[0])] for k in (0,2,4))
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def H(Dq,B,Cc):
    F={0:0,2:49*B+7*Cc,4:441*Cc/35}
    V=np.zeros((5,5))
    for i,m in enumerate(ms):
        V[i,i]={0:6,1:-4,2:1}[abs(m)]*Dq
    V[0,4]=V[4,0]=5*Dq
    h1=np.zeros((10,10))
    for i in range(10):
        for j in range(10):
            if so[i][1]==so[j][1]: h1[i,j]=V[ms.index(so[i][0]),ms.index(so[j][0])]
    N=len(dets);M=np.zeros((N,N))
    for I,d in enumerate(dets):
        # one-body
        for p in d:
            for q in range(10):
                if q in d and q!=p: continue
                nd=list(d); pos=nd.index(p); nd[pos]=q
                sg=1
                arr=nd[:]
                # sort sign
                perm=sorted(range(3),key=lambda i:arr[i]); 
                sg=np.linalg.det(np.eye(3)[perm])
                M[idx[tuple(sorted(arr))],I]+=sg*h1[q,p]
        # two-body
        for p,q in itertools.combinations(d,2):
            rest=[x for x in d if x not in (p,q)]
            for r in range(10):
                for s in range(10):
                    if r==s: continue
                    if (r in rest) or (s in rest): continue
                    val=0.5*(coul(so[r],so[s],so[p],so[q],F)-coul(so[r],so[s],so[q],so[p],F))
                    if abs(val)<1e-12: continue
                    # a_r+ a_s+ a_q a_p |d>, compute via ordered: replace
                    arr=[r,s]+rest; orig=[p,q]+rest
                    s1=np.linalg.det(np.eye(3)[sorted(range(3),key=lambda i:orig[i])])
                    s2=np.linalg.det(np.eye(3)[sorted(range(3),key=lambda i:arr[i])])
                    M[idx[tuple(sorted(arr))],I]+=2*val*s1*s2
    return M
def levels(Dq,B,Cc):
    e=np.linalg.eigvalsh(H(Dq,B,Cc)); e=e-e[0]
    return np.round(e,1)
e=levels(1750,618,4*618)
print(sorted(set(e))[:8])
def f(Cc):
    e=sorted(set(levels(1750,618,Cc))); return e[1]-12090
Cs=brentq(f,1500,4000); print(Cs, Cs/618, sorted(set(levels(1750,618,Cs)))[:6])
