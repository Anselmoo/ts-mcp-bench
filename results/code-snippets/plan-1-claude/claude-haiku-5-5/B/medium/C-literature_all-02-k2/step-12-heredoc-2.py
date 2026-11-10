import numpy as np, itertools
from functools import lru_cache
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve
l=2; ms=list(range(-2,3))
@lru_cache(None)
def G(l1,l2,l3,m1,m2,m3): return float(gaunt(l1,l2,l3,m1,m2,m3))
def Ysum(ma,mc,k,q):
    if mc-ma!=q: return 0.0
    return (-1)**(ma+q)*G(l,l,k,-ma,mc,-q)
def Yprod(mb,md,k,q):
    if mb-md!=q: return 0.0
    return (-1)**mb*G(l,l,k,-mb,md,q)
def Oint(ma,mc):
    tot=0.0
    for (q,coef) in [(0,1.0),(4,np.sqrt(5/14)),(-4,np.sqrt(5/14))]:
        if mc-ma+q!=0: continue
        tot+=coef*(-1)**ma*G(l,4,l,-ma,q,mc)
    return tot
Om=np.array([[Oint(a,c) for c in ms] for a in ms])
w=np.linalg.eigvalsh(Om); SP=w[-1]-w[0]
h1=Om*(10/SP)
def ang(a,b,c,d,k):
    return 4*np.pi/(2*k+1)*sum(Ysum(a,c,k,q)*Yprod(b,d,k,q) for q in range(-k,k+1))
A={}
for a,b,c,d in itertools.product(ms,repeat=4):
    for k in (0,2,4): A[(a,b,c,d,k)]=ang(a,b,c,d,k)
print("exch sum k2:",sum(A[(a,b,b,a,2)] for a in ms for b in ms), "direct k2:",sum(A[(a,b,a,b,2)] for a in ms for b in ms))
so=[(m,s) for m in ms for s in (1,-1)]; N=len(so)
states=list(itertools.combinations(range(N),2)); idx={s:i for i,s in enumerate(states)}
def apply_ops(ops,st):
    occ=list(st); sign=1
    for typ,o in reversed(ops):
        if typ=='a':
            if o not in occ: return None
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None
            p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
    return sign, tuple(sorted(occ))
ee=[]
for a,b,c,d in itertools.product(range(N),repeat=4):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
    if sa!=sc or sb!=sd: continue
    v2=A[(ma,mb,mc,md,2)]; v4=A[(ma,mb,mc,md,4)]
    if abs(v2)<1e-14 and abs(v4)<1e-14: continue
    ee.append((a,b,c,d,v2,v4))
one=[(a,b,h1[ms.index(so[a][0]),ms.index(so[b][0])]) for a in range(N) for b in range(N) if so[a][1]==so[b][1]]
Hcf=np.zeros((45,45)); H2=np.zeros((45,45)); H4=np.zeros((45,45))
for col,st in enumerate(states):
    for a,b,h in one:
        if abs(h)<1e-14: continue
        r=apply_ops([('c',a),('a',b)],st)
        if r: Hcf[idx[r[1]],col]+=r[0]*h
    for a,b,c,d,v2,v4 in ee:
        r=apply_ops([('c',a),('c',b),('a',d),('a',c)],st)
        if r: H2[idx[r[1]],col]+=0.5*r[0]*v2; H4[idx[r[1]],col]+=0.5*r[0]*v4
def spectrum(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9
    H=Dq*Hcf+F2*H2+F4*H4
    up=[i for i,s in enumerate(states) if so[s[0]][1]==1 and so[s[1]][1]==1]
    mz0=[i for i,s in enumerate(states) if so[s[0]][1]!=so[s[1]][1]]
    T=np.sort(np.linalg.eigvalsh(H[np.ix_(up,up)]))
    M0=list(np.sort(np.linalg.eigvalsh(H[np.ix_(mz0,mz0)])))
    for t in T:
        M0.pop(int(np.argmin([abs(x-t) for x in M0])))
    return T,np.array(M0),H
T,S,_=spectrum(0,1,0)
print("free ion B=1,C=0 triplets:",np.round(T,4))
print("singlets:",np.round(S,4))
T,S,_=spectrum(0,0,1)
print("free ion C=1 triplets:",np.round(T,4)); print("singlets:",np.round(S,4))
