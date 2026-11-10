import numpy as np, itertools, functools
from sympy.physics.wigner import wigner_3j
B=1.0;C=3473/800
F2=49*B+7*C;F4=63*C/5
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
@functools.lru_cache(None)
def ck(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
Fk={0:0,2:F2/49,4:F4/441}
@functools.lru_cache(None)
def g(a,b,c,d):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=a,b,c,d
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0
    return sum(Fk[k]*ck(k,m1,m3)*ck(k,m4,m2) for k in (0,2,4))
def one(Dq):
    h=np.zeros((10,10));V=np.zeros((5,5));idx={m:i for i,m in enumerate(ms)}
    for m in(-1,1):V[idx[m],idx[m]]=-4*Dq
    V[idx[0],idx[0]]=6*Dq
    V[idx[2],idx[2]]=V[idx[-2],idx[-2]]=Dq
    V[idx[2],idx[-2]]=V[idx[-2],idx[2]]=5*Dq
    for i,(m,s) in enumerate(orbs):
        for j,(n,t) in enumerate(orbs):
            if s==t:h[i,j]=V[idx[m],idx[n]]
    return h
dets=[d for d in itertools.combinations(range(10),5) if sum(orbs[i][1] for i in d)==0.5]
di={d:i for i,d in enumerate(dets)}
def apply(ops,d):
    d=list(d);sign=1
    for typ,i in reversed(ops):
        if typ=='a':
            if i not in d:return None,0
            p=d.index(i);sign*=(-1)**p;d.pop(p)
        else:
            if i in d:return None,0
            p=sum(1 for x in d if x<i);sign*=(-1)**p;d.insert(p,i)
    return tuple(d),sign
N=len(dets)
M2=np.zeros((N,N))
quads=[(p,q,r,s) for p in range(10) for q in range(10) for r in range(10) for s in range(10) if g(orbs[p],orbs[q],orbs[r],orbs[s])!=0]
for d in dets:
    a=di[d]
    for p,q,r_,s_ in quads:
        r,s=apply([('c',p),('c',q),('a',s_),('a',r_)],d)
        if r is not None:M2[di[r],a]+=0.5*g(orbs[p],orbs[q],orbs[r_],orbs[s_])*s
M1=np.zeros((N,N))
def H(Dq):
    h=one(Dq);M=M2.copy()
    for d in dets:
        a=di[d]
        for i in range(10):
            for j in range(10):
                if h[i,j]!=0:
                    r,s=apply([('c',i),('a',j)],d)
                    if r is not None:M[di[r],a]+=h[i,j]*s
    return M
for x in (1.45,2.55,3.25):
    w=np.linalg.eigvalsh(H(x));w=w-w[0]
    u=[]
    for e in w:
        if not u or abs(e-u[-1][0])>1e-3:u.append([round(e,3),1])
        else:u[-1][1]+=1
    print(x,u[:9])
