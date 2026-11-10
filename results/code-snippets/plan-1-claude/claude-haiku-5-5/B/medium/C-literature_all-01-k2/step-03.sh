mkdir -p /tmp/ni && cat > /tmp/ni/d8.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
from functools import lru_cache

ms = [-2,-1,0,1,2]
# spin orbitals: index = 2*orb + s, s=0 up, 1 down
orbs = [(m,s) for m in ms for s in (0,1)]
NSO = 10
@lru_cache(None)
def G(l1,l2,l3,m1,m2,m3):
    return float(gaunt(l1,l2,l3,m1,m2,m3))
def angular(k,ma,mb,mc,md):
    # <ma mb | 1/r12 | mc md> / F^k  (without radial), summed over q
    tot=0.0
    for q in range(-k,k+1):
        g1=G(2,k,2,-ma,-q,mc)
        if g1==0: continue
        g2=G(2,k,2,-mb,q,md)
        if g2==0: continue
        tot+= (-1)**(ma+q) * g1 * (-1)**mb * g2
    return 4*np.pi/(2*k+1)*tot
def Vint(F, a, b, c, d):
    # a,b,c,d are m values; F dict k->Slater integral
    return sum(F[k]*angular(k,a,b,c,d) for k in (0,2,4))

def build(B, C, Dq):
    F4 = C*441/35.0
    F2 = 49*B + 5*F4/9*1.0  # placeholder replaced below
    # Griffith: B = F2/49 - 5F4/441 ; C = 35F4/441
    F4 = 441*C/35.0
    F2 = 49*(B + 5*F4/441.0)
    F = {0:0.0, 2:F2, 4:F4}
    # one-electron tetrahedral: e (dz2,dx2-y2) -6Dq, t2 +4Dq
    s2=np.sqrt(2)
    vecs_e = [np.array([0,0,1,0,0],complex), np.array([1,0,0,0,1],complex)/s2]
    vecs_t = [np.array([-1j,0,0,0,1j],complex)/s2, np.array([0,1,0,-1,0],complex)/s2, np.array([0,1j,0,1j,0],complex)/s2]
    h = np.zeros((5,5),complex)
    for v in vecs_e: h += -6*Dq*np.outer(v,v.conj())
    for v in vecs_t: h += 4*Dq*np.outer(v,v.conj())
    # full spin-orbital one-body
    h1 = np.zeros((NSO,NSO),complex)
    for i,(m,s) in enumerate(orbs):
        for j,(mp,sp) in enumerate(orbs):
            if s==sp: h1[i,j]=h[ms.index(m),ms.index(mp)]
    # two-body V_ijkl = <ij|1/r|kl>, spin-diagonal
    V = np.zeros((NSO,)*4)
    for i,(m1,s1) in enumerate(orbs):
        for j,(m2,s2_) in enumerate(orbs):
            for k,(m3,s3) in enumerate(orbs):
                for l,(m4,s4) in enumerate(orbs):
                    if s1==s3 and s2_==s4:
                        V[i,j,k,l]=Vint(F,m1,m2,m3,m4)
    return h1,V

# Fock-space via determinant basis with N=8, Ms=1 (nup=5, ndn=3)
def dets():
    out=[]
    for occ in itertools.combinations(range(NSO),8):
        nup=sum(1 for o in occ if orbs[o][1]==0)
        if nup==5: out.append(occ)
    return out
D = dets()
def apply_op(occ, ops):
    # ops: list of (type, idx) applied right to left; type 'c' or 'a'
    st=list(occ); sign=1
    for typ,idx in reversed(ops):
        if typ=='c':
            if idx in st: return None,0
            # insert: sign = (-1)^(number of occupied below idx)
            n=sum(1 for o in st if o<idx); sign*= (-1)**n
            st.append(idx); st.sort()
        else:
            if idx not in st: return None,0
            n=sum(1 for o in st if o<idx); sign*= (-1)**n
            st.remove(idx)
    return tuple(st),sign
def Hmat(B,C,Dq):
    h1,V = build(B,C,Dq)
    idx={d:i for i,d in enumerate(D)}
    H=np.zeros((len(D),len(D)),complex)
    for col,d in enumerate(D):
        for i in range(NSO):
            for j in range(NSO):
                if h1[i,j]!=0:
                    r,s=apply_op(d,[('c',i),('a',j)])
                    if r is not None: H[idx[r],col]+=h1[i,j]*s
        for i in range(NSO):
            for j in range(NSO):
                for k in range(NSO):
                    for l in range(NSO):
                        v=V[i,j,k,l]
                        if abs(v)<1e-12: continue
                        r,s=apply_op(d,[('c',i),('c',j),('a',l),('a',k)])
                        if r is not None: H[idx[r],col]+=0.5*v*s
    return H
def levels(B,C,Dq):
    H=Hmat(B,C,Dq)
    assert np.allclose(H,H.conj().T)
    return np.sort(np.linalg.eigvalsh(H).real)
if __name__=="__main__":
    print(len(D))
    ev=levels(1000,4500,0)
    print(np.round(ev,1))
EOF
cd /tmp/ni && time python3 d8.py