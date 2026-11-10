mkdir -p /w && cat > /w/ligf.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import pi, sqrt

# complex d orbitals m=-2..2 -> index m+2
def gaunt_num(l1,l2,l3,m1,m2,m3):
    return float(gaunt(l1,l2,l3,m1,m2,m3))

def Ang(k, oa, oc, ob, od):
    # <oa ob | C^k_{-q}(1) C^k_q(2) | oc od> summed over q with (-1)^q
    ma, mc, mb, md = oa-2, oc-2, ob-2, od-2
    tot = 0.0
    for q in range(-k, k+1):
        # <a|C^k_{-q}|c> = sqrt(4pi/(2k+1)) * (-1)^{ma} * gaunt(2,k,2,-ma,-q,mc)
        if abs(-q)>k: continue
        if -ma - q != mc: pass
        g1 = gaunt_num(2,k,2,-ma,-q,mc) if abs(-ma-q+ mc)==0 else 0.0
        g1 = gaunt_num(2,k,2,-ma,-q,mc)
        if g1==0: continue
        # <b|C^k_q|d> = sqrt(4pi/(2k+1)) * (-1)^{mb} * gaunt(2,k,2,-mb,q,md)
        g2 = gaunt_num(2,k,2,-mb,q,md)
        tot += (-1)**(q%2) * (-1)**ma * g1 * (-1)**mb * g2 * (4*pi/(2*k+1))
    return tot

def build(F0,F2,F4):
    Fk={0:F0,2:F2,4:F4}
    # spin-orbital index s=2*o+sigma
    N=10
    V = np.zeros((N,N,N,N))
    for oa,ob,oc,od in itertools.product(range(5),repeat=4):
        val=0.0
        for k in (0,2,4):
            val += Fk[k]*Ang(k,oa,oc,ob,od)
        if abs(val)<1e-12: continue
        for sa,sb,sc,sd in itertools.product(range(2),repeat=4):
            if sa!=sc or sb!=sd: continue
            V[2*oa+sa,2*ob+sb,2*oc+sc,2*od+sd]=val
    return V

def ligand_h(Dq):
    # real orbitals in complex basis
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

def ham(Dq,F0,F2,F4):
    V=build(F0,F2,F4)
    h5=ligand_h(Dq)
    N=10
    h=np.zeros((N,N),complex)
    for o1 in range(5):
        for o2 in range(5):
            for sg in range(2):
                h[2*o1+sg,2*o2+sg]=h5[o1,o2]
    dets=[d for d in itertools.combinations(range(N),7)
          if sum(1 for s in d if s%2==0)==5]  # n_up=5 (even index = spin up), Ms=3/2
    idx={d:i for i,d in enumerate(dets)}
    M=len(dets)
    H=np.zeros((M,M),complex)
    def apply(ops, det):
        # ops: list of (type,index) applied right to left; returns (sign, newdet) or None
        occ=list(det); sign=1
        for typ,i in ops:
            if typ=='a':   # annihilate
                if i not in occ: return None
                p=occ.index(i); sign*= (-1)**p; occ.pop(p)
            else:          # create
                if i in occ: return None
                # insert sorted
                p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
        return sign, tuple(occ)
    for j,dj in enumerate(dets):
        # one-body
        for a in range(N):
            for c in range(N):
                if h[a,c]==0: continue
                r=apply([('c',a),('a',c)],dj)
                if r is None: continue
                s,nd=r
                if nd in idx: H[idx[nd],j]+=s*h[a,c]
        # two-body: 1/2 sum V[a,b,c,d] a+a a+b a_d a_c
        for a,b,c,d in itertools.product(range(N),repeat=4):
            v=V[a,b,c,d]
            if v==0: continue
            r=apply([('c',a),('c',b),('a',d),('a',c)],dj)
            if r is None: continue
            s,nd=r
            if nd in idx: H[idx[nd],j]+=0.5*s*v
    return H, dets

if __name__=="__main__":
    B=1.0; C=4.0
    F4=441*C/35; F2=(441*B+5*F4)/9
    print("F2,F4",F2,F4)
    H,dets=ham(0.0,0.0,F2,F4)
    print(np.round(np.linalg.eigvalsh(H),6))
EOF
cd /w && python3 ligf.py