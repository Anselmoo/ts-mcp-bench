cd /tmp && cat > /dev/null << 'EOF'
placeholder
EOF
python3 - << 'EOF'
import numpy as np, itertools
from numpy.polynomial.legendre import leggauss
from scipy.special import eval_legendre
nt, nphi = 60, 120
xg, wg = leggauss(nt)
th = np.arccos(xg); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = (np.repeat(wg[:,None],nphi,1)*(2*np.pi/nphi)).ravel()
x = (np.sin(TH)*np.cos(PH)).ravel(); y=(np.sin(TH)*np.sin(PH)).ravel(); z=np.cos(TH).ravel()
raw = [x*y, x*z, y*z, x*x-y*y, (3*z*z-1)/2]
orb = np.array([f/np.sqrt(np.sum(W*f*f)) for f in raw])
assert np.allclose((orb*W)@orb.T, np.eye(5), atol=1e-10)
cg = np.outer(x,x)+np.outer(y,y)+np.outer(z,z)
Pk = {k: eval_legendre(k, np.clip(cg,-1,1)) for k in (0,2,4)}
pairs = [(a,c) for a in range(5) for c in range(5)]
rho = np.array([orb[a]*orb[c] for a,c in pairs])
A = {k: (rho*W) @ Pk[k] @ (rho*W).T for k in (0,2,4)}
idx = {p:i for i,p in enumerate(pairs)}
# sanity: a2 for d-shell: <xy|1/r|xy;...> check k=0 gives 1 for same-orbital pair
print("A0 diag", A[0][idx[(0,0)],idx[(0,0)]], A[0][idx[(0,0)],idx[(1,1)]])

def Vmat(F):
    V = np.zeros((10,10,10,10))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        val = sum(F[k]*A[k][idx[(a,c)], idx[(b,d)]] for k in F)
        for s1 in (0,1):
            for s2 in (0,1):
                V[2*a+s1,2*b+s2,2*c+s1,2*d+s2] = val
    return V

dets = [tuple(sorted(c)) for c in itertools.combinations(range(10),6)]
didx = {d:i for i,d in enumerate(dets)}
def annih(k, st):
    if k not in st: return None
    p = st.index(k); return ((-1)**p, tuple(m for m in st if m!=k))
def create(i, st):
    if i in st: return None
    p = sum(1 for m in st if m<i); return ((-1)**p, tuple(sorted(st+(i,))))

# precompute two-body action
def build_H(F, Dq):
    V = Vmat(F)
    N=len(dets); H=np.zeros((N,N))
    h = np.array([-4,-4,-4,6,6])*Dq
    nz = [(i,j,k,l,V[i,j,k,l]) for i,j,k,l in itertools.product(range(10),repeat=4) if abs(V[i,j,k,l])>1e-12]
    for n,st in enumerate(dets):
        for m in st: H[n,n]+=h[m//2]
        for (i,j,k,l,v) in nz:
            r1=annih(k,st)
            if r1 is None: continue
            s1,c1=r1
            r2=annih(l,c1)
            if r2 is None: continue
            s2,c2=r2
            r3=create(j,c2)
            if r3 is None: continue
            s3,c3=r3
            r4=create(i,c3)
            if r4 is None: continue
            s4,c4=r4
            H[didx[c4],n]+=0.5*v*s1*s2*s3*s4
    return H

# S^2 and C4
def Sz_ops():
    pass
# total S^2 via Sz and S+ S-
def S2matrix():
    N=len(dets); Sp=np.zeros((N,N)); Sz=np.zeros(N)
    for n,st in enumerate(dets):
        Sz[n]=sum(0.5 if m%2==0 else -0.5 for m in st)
        for o in range(5):
            # S+ = sum_o c+_{o,up} c_{o,down}
            r1=annih(2*o+1,st)
            if r1 is None: continue
            s1,c1=r1
            r2=create(2*o,c1)
            if r2 is None: continue
            s2,c2=r2
            Sp[didx[c2],n]+=s1*s2
    S2 = Sp.T@Sp + np.diag(Sz*(Sz-1)) + 0  # S-S+ = S^2 - Sz^2 - Sz ; use S^2 = S-S+ + Sz^2+Sz ; S-S+ = Sp^T Sp
    S2 = Sp.T@Sp + np.diag(Sz**2+Sz)
    return S2
S2 = S2matrix()
print("S2 eig sample", np.unique(np.round(np.linalg.eigvalsh(S2),6)))

perm = {0:(0,-1),1:(2,1),2:(1,-1),3:(3,-1),4:(4,1)}
N=len(dets); U=np.zeros((N,N))
for n,st in enumerate(dets):
    sign=1; cur=(); ok=True
    for m in st:
        o,s=divmod(m,2); no,sg=perm[o]; sign*=sg
        r=create(2*no+s,cur)
        if r is None: ok=False;break
        ss,cur=r; sign*=ss
    if ok: U[didx[cur],n]=sign
print("C4 orthogonal", np.allclose(U@U.T,np.eye(N)))

def spectrum(B, x):
    Dq = x*B
    F4 = 441*4.5*B/35; F2 = (441*B+5*F4)/9
    H = build_H({2:F2,4:F4}, Dq)
    # singlet subspace: null space of S2
    w,v = np.linalg.eigh(S2)
    Q = v[:, np.abs(w)<1e-8]
    Hs = Q.T@H@Q; Us = Q.T@U@Q
    # diagonalize H; use H + tiny*U to split? U commutes with H; do cluster analysis
    E,Vv = np.linalg.eigh(Hs)
    levels=[]
    i=0
    while i < len(E):
        j=i
        while j+1<len(E) and abs(E[j+1]-E[i])<1e-6*max(1,abs(E[i])): j+=1
        block = Vv[:,i:j+1]
        tr = np.trace(block.T@Us@block)
        levels.append((E[i], j-i+1, round(tr,6)))
        i=j+1
    return levels

if __name__=="__main__":
    pass
import sys
for x in [1.0]:
    lv = spectrum(1.0, x)
    for l in lv[:12]: print(l)
EOF