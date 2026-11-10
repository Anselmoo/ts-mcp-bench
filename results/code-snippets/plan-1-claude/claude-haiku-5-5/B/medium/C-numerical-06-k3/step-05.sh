cd /tmp && cat > fit.py << 'EOF'
import numpy as np, itertools
exec(open('/dev/stdin').read()) if False else None
EOF
python3 - << 'EOF'
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
V=build({0:0.0,2:1.0,4:0.0})  # placeholder
def ham_parts(Dq):
    h5=ligand_h(Dq); h=np.zeros((N,N),complex)
    for o1 in range(5):
        for o2 in range(5):
            for sg in range(2): h[2*o1+sg,2*o2+sg]=h5[o1,o2]
    return h
# Coulomb matrix per Fk component (linear in F2,F4)
VF={}
for k in (2,4):
    Vk=build({0:0.0,2:(1.0 if k==2 else 0.0),4:(1.0 if k==4 else 0.0)})
    nz=[(a,b,c,d,Vk[a,b,c,d]) for a,b,c,d in itertools.product(range(N),repeat=4) if Vk[a,b,c,d]!=0]
    M=len(dets); Hk=np.zeros((M,M))
    for j,dj in enumerate(dets):
        for a,b,c,d,v in nz:
            r=apply([('c',a),('c',b),('a',d),('a',c)],dj)
            if r is None: continue
            s,nd=r
            if nd in idx: Hk[idx[nd],j]+=0.5*s*v
    VF[k]=Hk
# one-body matrix in det space
def H1(Dq):
    h=ham_parts(Dq); M=len(dets); H=np.zeros((M,M),complex)
    for j,dj in enumerate(dets):
        for a in range(N):
            for c in range(N):
                if abs(h[a,c])<1e-14: continue
                r=apply([('c',a),('a',c)],dj)
                if r is None: continue
                s,nd=r
                if nd in idx: H[idx[nd],j]+=s*h[a,c]
    return H
def levels(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9
    H=H1(Dq)+F2*VF[2]+F4*VF[4]
    return np.linalg.eigvalsh(H)
def distinct(ev,tol=1e-6):
    out=[]
    for e in ev:
        if not out or abs(e-out[-1][0])>tol: out.append([e,1])
        else: out[-1][1]+=1
    return out
print("Dq=0,B=1,C=4:",distinct(levels(0,1,4)))
# check C-independence
print("C=0 vs C=4 at Dq=0.5:",np.round(levels(0.5,1,0),4)[:10]," | ",np.round(levels(0.5,1,4),4)[:10])
EOF