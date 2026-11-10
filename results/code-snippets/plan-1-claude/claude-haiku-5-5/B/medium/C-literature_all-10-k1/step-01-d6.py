import numpy as np, itertools
from numpy.polynomial.legendre import leggauss
from scipy.optimize import brentq
from scipy.special import eval_legendre

# real d orbitals on unit sphere: index o: 0 xy,1 xz,2 yz,3 x2-y2,4 z2
nt, nphi = 60, 120
xg, wg = leggauss(nt)
th = np.arccos(xg); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = (np.repeat(wg[:,None],nphi,1)*(2*np.pi/nphi)).ravel()
x = (np.sin(TH)*np.cos(PH)).ravel(); y=(np.sin(TH)*np.sin(PH)).ravel(); z=np.cos(TH).ravel()
raw = [x*y, x*z, y*z, x*x-y*y, (3*z*z-1)/2]
orb = []
for f in raw:
    orb.append(f/np.sqrt(np.sum(W*f*f)))
orb = np.array(orb)          # 5 x N
# orthonormality check
G = (orb*W) @ orb.T
assert np.allclose(G, np.eye(5), atol=1e-10)
# angle matrix cos gamma
cg = np.outer(x,x)+np.outer(y,y)+np.outer(z,z)
Pk = {k: eval_legendre(k, np.clip(cg,-1,1)) for k in (0,2,4)}
pairs = [(a,c) for a in range(5) for c in range(5)]
rho = np.array([orb[a]*orb[c] for a,c in pairs])   # 25 x N
A = {}
for k in (0,2,4):
    M = (rho*W) @ Pk[k] @ (rho*W).T   # 25x25 : int rho_ac(1) P_k rho_bd(2)
    A[k] = M
idx = {p:i for i,p in enumerate(pairs)}
def ang(k,a,c,b,d):
    # <ab|1/r12|cd> angular part : electron1 a*->c, electron2 b*->d
    return A[k][idx[(a,c)], idx[(b,d)]]

# spin orbitals: mode = 2*o + s
def Vmat(F):
    V = np.zeros((10,10,10,10))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        for s1 in (0,1):
            for s2 in (0,1):
                val = sum(F[k]*ang(k,a,c,b,d) for k in F)
                V[2*a+s1,2*b+s2,2*c+s1,2*d+s2] = val
    return V

# Fock space, determinants with 6 electrons
dets = [tuple(sorted(c)) for c in itertools.combinations(range(10),6)]
didx = {d:i for i,d in enumerate(dets)}
def annih(k, st):
    if k not in st: return None
    p = st.index(k); return ((-1)**p, tuple(m for m in st if m!=k))
def create(i, st):
    if i in st: return None
    p = sum(1 for m in st if m<i); return ((-1)**p, tuple(sorted(st+(i,))))
def apply_ops(ops, st):
    # ops list applied right-to-left: ops = [(type,mode),...] applied in order given (first applied first)
    sign = 1; cur = st
    for typ,m in ops:
        r = annih(m,cur) if typ=='a' else create(m,cur)
        if r is None: return None
        s,cur = r; sign*=s
    return sign,cur

def build_H(F, Dq, Bscale=1.0):
    V = Vmat(F)
    N=len(dets); H=np.zeros((N,N))
    # one-electron: eg (dz2 idx4, dx2-y2 idx3) +6Dq, t2g -4Dq
    h = np.array([-4,-4,-4,6,6])*Dq
    for n,st in enumerate(dets):
        for m in st:
            o=m//2
            H[n,n]+=h[o]
        # two-electron: 1/2 sum V_ijkl c+_i c+_j c_l c_k
        for i in range(10):
          for j in range(10):
            for k in range(10):
              for l in range(10):
                v = V[i,j,k,l]
                if abs(v)<1e-12: continue
                r = apply_ops([('a',k),('a',l),('c',j),('c',i)], st)
                if r is None: continue
                s,new = r
                H[didx[new],n] += 0.5*v*s
    return H

def C4_matrix():
    # C4 about z: x->y, y->-x ; orbitals: xy->-xy, xz->yz, yz->-xz, x2-y2 -> -(x2-y2), z2->z2
    perm = {0:(0,-1),1:(2,1),2:(1,-1),3:(3,-1),4:(4,1)}
    N=len(dets); U=np.zeros((N,N))
    for n,st in enumerate(dets):
        sign=1; new=[]
        # apply c+_{new} for each occupied in order
        cur=()
        ok=True
        for m in st:
            o,s=divmod(m,2)
            no,sg=perm[o]
            sign*=sg
            r=create(2*no+s,cur)
            if r is None: ok=False;break
            ss,cur=r; sign*=ss
        if ok: U[didx[cur],n]=sign
    return U
