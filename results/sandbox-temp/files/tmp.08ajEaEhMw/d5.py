import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
so=[(m,s) for s in (0,1) for m in ms]
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,m1-m2,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def g(a,b,c,d,F):
    if a+b!=c+d: return 0
    return sum(F[k]*C[k,a,c]*C[k,d,b] for k in (0,2,4))
dets=[d for d in itertools.combinations(range(10),5) if sum(so[x][1] for x in d)==4]
idx={d:i for i,d in enumerate(dets)}
def build(Dq,B,Cc):
    F={0:0,2:49*B+7*Cc,4:441*Cc/35}
    V=np.zeros((5,5))
    for i,m in enumerate(ms): V[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    N=len(dets);H=np.zeros((N,N))
    for I,d in enumerate(dets):
        occ=list(d)
        for p in occ:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=V[ms.index(so[q][0]),ms.index(so[p][0])]
                if v==0 or (q!=p and q in occ): continue
                lst=list(occ);k=lst.index(p);sg=(-1)**k;lst.pop(k)
                k=sum(1 for y in lst if y<q);sg*=(-1)**k;lst.insert(k,q)
                H[idx[tuple(lst)],I]+=sg*v
        for p,q in itertools.combinations(occ,2):
            rest=[x for x in occ if x not in (p,q)]
            for r in range(10):
              for s in range(10):
                if r==s or r in rest or s in rest: continue
                if so[r][1]!=so[p][1] or so[s][1]!=so[q][1]: continue
                v=g(so[r][0],so[s][0],so[p][0],so[q][0],F)
                if v==0: continue
                lst=list(occ); sg=1
                for x in (p,q):
                    k=lst.index(x); sg*=(-1)**k; lst.pop(k)
                for x in (s,r):
                    k=sum(1 for y in lst if y<x); sg*=(-1)**k; lst.insert(k,x)
                H[idx[tuple(lst)],I]+=sg*v
    return H
def levels(Dq,B,Cc):
    e=np.linalg.eigvalsh(build(Dq,B,Cc)); e=e-e[0]
    # group
    out=[];i=0
    while i<len(e):
        j=i
        while j<len(e) and abs(e[j]-e[i])<1e-3: j+=1
        out.append((round(e[i],1),j-i)); i=j
    return out
print(levels(0,1000,4000)[:6])
print(levels(800,700,3200)[:6])
def res(x):
    L=levels(*x)
    return [L[1][0]-19180,L[2][0]-22130,L[3][0]-23370]
s=least_squares(res,[800,700,3000]);print(s.x,res(s.x),levels(*s.x)[:6])
def res2(x):
    L=levels(*x)
    return [L[1][0]-19180,L[2][0]-22130,10*x[1]+5*x[2]-23370]
s=least_squares(res2,[700,700,3200]);print(s.x,res2(s.x),levels(*s.x)[:6])
for st in ([1000,600,3500],[500,800,3000],[900,650,3300]):
    s=least_squares(res2,st);print(s.x,res2(s.x))
from scipy.optimize import minimize
f=lambda x: sum(r*r for r in res2(x))
s=minimize(f,[600,780,3100],method='Nelder-Mead',options={'xatol':0.01,'fatol':1e-4,'maxiter':4000});print(s.x,res2(s.x),levels(*s.x)[:6])
