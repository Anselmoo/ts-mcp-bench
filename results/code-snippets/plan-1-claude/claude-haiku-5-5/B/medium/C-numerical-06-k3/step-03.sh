mkdir -p /tmp/w && cd /tmp/w && cat > ligf.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import pi, sqrt
from functools import lru_cache

@lru_cache(None)
def G(l1,l2,l3,m1,m2,m3):
    return float(gaunt(l1,l2,l3,m1,m2,m3))

def Ang(k, oa, oc, ob, od):
    ma, mc, mb, md = oa-2, oc-2, ob-2, od-2
    tot = 0.0
    for q in range(-k, k+1):
        g1 = G(2,k,2,-ma,-q,mc)
        if g1==0: continue
        g2 = G(2,k,2,-mb,q,md)
        if g2==0: continue
        tot += (-1)**(q%2) * (-1)**ma * g1 * (-1)**mb * g2 * (4*pi/(2*k+1))
    return tot

def build(Fk):
    N=10
    V = np.zeros((N,N,N,N))
    for oa,ob,oc,od in itertools.product(range(5),repeat=4):
        val=sum(Fk[k]*Ang(k,oa,oc,ob,od) for k in (0,2,4))
        if abs(val)<1e-12: continue
        for sa,sb in itertools.product(range(2),repeat=2):
            V[2*oa+sa,2*ob+sb,2*oc+sa,2*od+sb]=val
    return V

def ligand_h(Dq):
    h=np.zeros((5,5),complex)
    s2=sqrt(2)
    def vec(d):
        v=np.zeros(5,complex)
        for m,c in d.items(): v[m+2]=c
        return v
    dz2 = vec({0:1})
    dx2 = vec({2:1/s2, -2:1/s2})
    dxy = vec({2:1/(1j*s2), -2:-1/(1j*s2)})
    dxz = vec({1:-1/s2, -1:1/s2})
    dyz = vec({1:1j/s2, -1:1j/s2})
    for v,e in [(dxy,-4*Dq),(dxz,-4*Dq),(dyz,-4*Dq),(dz2,6*Dq),(dx2,6*Dq)]:
        v=v/np.linalg.norm(v)
        h+= e*np.outer(v,v.conj())
    return h

def apply(ops, det):
    occ=list(det); sign=1
    for typ,i in ops:
        if typ=='a':
            if i not in occ: return None
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return sign, tuple(occ)

def ham(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9; F0=0.0  # F0 only shifts constant
    V=build({0:F0,2:F2,4:F4})
    h5=ligand_h(Dq)
    N=10
    h=np.zeros((N,N),complex)
    for o1 in range(5):
        for o2 in range(5):
            for sg in range(2):
                h[2*o1+sg,2*o2+sg]=h5[o1,o2]
    dets=[d for d in itertools.combinations(range(N),7)
          if sum(1 for s in d if s%2==0)==5]
    idx={d:i for i,d in enumerate(dets)}
    M=len(dets)
    H=np.zeros((M,M),complex)
    nz=[(a,b,c,d,V[a,b,c,d]) for a,b,c,d in itertools.product(range(N),repeat=4) if V[a,b,c,d]!=0]
    for j,dj in enumerate(dets):
        for a in range(N):
            for c in range(N):
                if h[a,c]==0: continue
                r=apply([('c',a),('a',c)],dj)
                if r is None: continue
                s,nd=r
                if nd in idx: H[idx[nd],j]+=s*h[a,c]
        for a,b,c,d,v in nz:
            r=apply([('c',a),('c',b),('a',d),('a',c)],dj)
            if r is None: continue
            s,nd=r
            if nd in idx: H[idx[nd],j]+=0.5*s*v
    return H

if __name__=="__main__":
    H=ham(0.0,1.0,4.0)
    print(np.round(np.linalg.eigvalsh(H),6))
EOF
python3 ligf.py