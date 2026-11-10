import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import pi, sqrt
from functools import lru_cache
@lru_cache(None)
def G(l1,l2,l3,m1,m2,m3): return float(gaunt(l1,l2,l3,m1,m2,m3))
def Ang(k,oa,oc,ob,od):
    ma,mc,mb,md=oa-2,oc-2,ob-2,od-2; tot=0.0
    for q in range(-k,k+1):
        g1=G(2,k,2,-ma,-q,mc)
        if g1==0: continue
        g2=G(2,k,2,-mb,q,md)
        if g2==0: continue
        tot+=(-1)**(q%2)*(-1)**ma*g1*(-1)**mb*g2*(4*pi/(2*k+1))
    return tot
def build(Fk):
    N=10; V=np.zeros((N,N,N,N))
    for oa,ob,oc,od in itertools.product(range(5),repeat=4):
        val=sum(Fk[k]*Ang(k,oa,oc,ob,od) for k in (0,2,4))
        if abs(val)<1e-12: continue
        for sa,sb in itertools.product(range(2),repeat=2):
            V[2*oa+sa,2*ob+sb,2*oc+sa,2*od+sb]=val
    return V
N=10
dets=[d for d in itertools.combinations(range(N),7) if sum(1 for s in d if s%2==0)==5]
idx={d:i for i,d in enumerate(dets)}
M=len(dets)
def ap(ops,det):
    occ=list(det); sign=1
    for typ,i in ops:
        if typ=='a':
            if i not in occ: return None
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return sign,tuple(occ)
def Hmat(V):
    H=np.zeros((M,M))
    nz=[(a,b,c,d,V[a,b,c,d]) for a,b,c,d in itertools.product(range(N),repeat=4) if V[a,b,c,d]!=0]
    for j,dj in enumerate(dets):
        for a,b,c,d,v in nz:
            r=ap([('c',a),('c',b),('a',d),('a',c)],dj)
            if r is None: continue
            s,nd=r
            if nd in idx: H[idx[nd],j]+=0.5*s*v
    return H
V2=build({0:0,2:1.0,4:0}); V4=build({0:0,2:0,4:1.0})
H2=Hmat(V2); H4=Hmat(V4)
np.save('H2.npy',H2); np.save('H4.npy',H4)
# one-body diag in real orbital basis
s2=sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
h5=np.zeros((5,5),complex)
for v,e in [(vec({2:1/(1j*s2),-2:-1/(1j*s2)}),-4),(vec({1:-1/s2,-1:1/s2}),-4),(vec({1:1j/s2,-1:1j/s2}),-4),(vec({0:1}),6),(vec({2:1/s2,-2:1/s2}),6)]:
    h5+=e*np.outer(v,v.conj())
h=np.zeros((N,N),complex)
for o1 in range(5):
    for o2 in range(5):
        for sg in range(2): h[2*o1+sg,2*o2+sg]=h5[o1,o2]
H1=np.zeros((M,M),complex)
for j,dj in enumerate(dets):
    for a in range(N):
        for c in range(N):
            if abs(h[a,c])<1e-14: continue
            r=ap([('c',a),('a',c)],dj)
            if r is None: continue
            s,nd=r
            if nd in idx: H1[idx[nd],j]+=s*h[a,c]
np.save('H1.npy',H1.real)
B=1.0;C=4.0
F4=441*C/35; F2=(441*B+5*F4)/9
for x in [0.001,0.5]:
    H=x*H1.real+F2*H2+F4*H4
    print(x,np.round(np.linalg.eigvalsh(H),4))
print("H1 eig",np.round(np.linalg.eigvalsh(H1.real),4))
print("H2 eig",np.round(np.linalg.eigvalsh(H2),4)); print("H4 eig",np.round(np.linalg.eigvalsh(H4),4))
