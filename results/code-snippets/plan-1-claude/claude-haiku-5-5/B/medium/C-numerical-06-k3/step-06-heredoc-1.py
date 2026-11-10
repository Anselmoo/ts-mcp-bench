import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import pi, sqrt
from functools import lru_cache
from scipy.optimize import brentq
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
def ligand_h(Dq):
    h=np.zeros((5,5),complex); s2=sqrt(2)
    def vec(d):
        v=np.zeros(5,complex)
        for m,c in d.items(): v[m+2]=c
        return v
    for v,e in [(vec({2:1/(1j*s2),-2:-1/(1j*s2)}),-4*Dq),(vec({1:-1/s2,-1:1/s2}),-4*Dq),
                (vec({1:1j/s2,-1:1j/s2}),-4*Dq),(vec({0:1}),6*Dq),(vec({2:1/s2,-2:1/s2}),6*Dq)]:
        v=v/np.linalg.norm(v); h+=e*np.outer(v,v.conj())
    return h
def apply(ops,det):
    occ=list(det); sign=1
    for typ,i in ops:
        if typ=='a':
            if i not in occ: return None
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return sign,tuple(occ)
N=10
dets=[d for d in itertools.combinations(range(N),7) if sum(1 for s in d if s%2==0)==5]
idx={d:i for i,d in enumerate(dets)}
M=len(dets)
VF={}
for k in (2,4):
    Vk=build({0:0.0,2:(1.0 if k==2 else 0.0),4:(1.0 if k==4 else 0.0)})
    nz=[(a,b,c,d,Vk[a,b,c,d]) for a,b,c,d in itertools.product(range(N),repeat=4) if Vk[a,b,c,d]!=0]
    Hk=np.zeros((M,M))
    for j,dj in enumerate(dets):
        for a,b,c,d,v in nz:
            r=apply([('c',a),('c',b),('a',d),('a',c)],dj)
            if r is None: continue
            s,nd=r
            if nd in idx: Hk[idx[nd],j]+=0.5*s*v
    VF[k]=Hk
def H1(Dq):
    h5=ligand_h(Dq); h=np.zeros((N,N),complex)
    for o1 in range(5):
        for o2 in range(5):
            for sg in range(2): h[2*o1+sg,2*o2+sg]=h5[o1,o2]
    H=np.zeros((M,M),complex)
    for j,dj in enumerate(dets):
        for a in range(N):
            for c in range(N):
                if abs(h[a,c])<1e-14: continue
                r=apply([('c',a),('a',c)],dj)
                if r is None: continue
                s,nd=r
                if nd in idx: H[idx[nd],j]+=s*h[a,c]
    return H
H1s={}
# Dq-dependence is linear in Dq: H1(Dq) = Dq*A + ... (ligand_h linear in Dq)
A=H1(1.0).real; 
assert np.allclose(H1(0.0),0)
F2,F4=None,None
def levels(x,B=1.0,C=4.0):
    F4=441*C/35; F2=(441*B+5*F4)/9
    H=x*A+F2*VF[2]+F4*VF[4]
    return np.linalg.eigvalsh(H)
def terms(x):
    ev=levels(x)
    # group
    groups=[]
    for e in ev:
        if groups and abs(e-groups[-1][0])<1e-6: groups[-1][1]+=1
        else: groups.append([e,1])
    return groups
for x in [0.0,0.5,1.0,1.5,2.0]:
    print(x,[(round(g,3),d) for g,d in terms(x)])
