mkdir -p /w && cat > /w/d2.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares
from scipy.integrate import quad

# angular grid
xg, wg = np.polynomial.legendre.leggauss(24)
phis = np.linspace(0, 2*np.pi, 48, endpoint=False); wp = 2*np.pi/48
TH, PH = np.meshgrid(np.arccos(xg), phis, indexing='ij')
W = np.outer(wg, np.full(len(phis), wp))
def Y(l, m):  # scipy: sph_harm(m, l, azimuth, polar)
    return sph_harm(m, l, PH, TH)
ms = list(range(-2, 3))
Yl = {m: Y(2, m) for m in ms}
def integ(f): return np.sum(W*f)
def Ykq(k, q): return Y(k, q)

# angular coefficients A_k[m1,m2,m3,m4] = (4pi/(2k+1)) sum_q int Y*m1 Ym3 Y*kq  * int Y*m2 Ym4 Ykq
def ang(k):
    A = np.zeros((5,5,5,5), complex)
    qs = range(-k, k+1)
    for i1,m1 in enumerate(ms):
        for i3,m3 in enumerate(ms):
            for q in qs:
                a = integ(np.conj(Yl[m1])*Yl[m3]*np.conj(Ykq(k,q)))
                for i2,m2 in enumerate(ms):
                    for i4,m4 in enumerate(ms):
                        b = integ(np.conj(Yl[m2])*Yl[m4]*Ykq(k,q))
                        A[i1,i2,i3,i4] += 4*np.pi/(2*k+1)*a*b
    return A
A = {k: ang(k) for k in (0,2,4)}

# cubic field one-electron matrix in m basis
X = np.sin(TH)*np.cos(PH); Yc = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
t2fs = [X*Yc, Yc*Z*0+Yc*0+ (Yc*Z), X*Z]  # xy, yz, xz (unnormalized)
t2fs = [X*Yc, Yc*Z, X*Z]
efs = [X**2-Yc**2, 3*Z**2-1]
def proj_vecs(fs):
    cs=[]
    for f in fs:
        c = np.array([integ(np.conj(Yl[m])*f) for m in ms])
        cs.append(c)
    # orthonormalize (Gram-Schmidt)
    out=[]
    for c in cs:
        v=c.copy()
        for u in out: v = v - np.vdot(u,v)*u
        out.append(v/np.linalg.norm(v))
    return out
def proj(vecs):
    P=np.zeros((5,5),complex)
    for v in vecs: P += np.outer(np.conj(v), v)
    return P
Pt2 = proj(proj_vecs(t2fs)); Pe = proj(proj_vecs(efs))
print("trace Pt2,Pe:", np.trace(Pt2).real, np.trace(Pe).real)
hcf = -4*Pt2 + 6*Pe   # per unit Dq

# spin-orbitals: (m index, spin) index s = 2*im + sp  (sp 0 up, 1 down)
def so(i_m, sp): return 2*i_m+sp
def build(Dq, Bv, Cv=None):
    if Cv is None: Cv = 4*Bv
    F4 = 441*Cv/35; F2 = (441*Bv+5*F4)/9
    F = {0:0.0, 2:F2, 4:F4}
    Vm = sum(F[k]*A[k] for k in (2,4))  # F0 term constant irrelevant for splittings (but include for completeness)
    Vm = Vm + F[0]*A[0]
    N=10
    h = np.zeros((N,N),complex)
    for a in range(5):
        for b in range(5):
            for sp in range(2):
                h[so(a,sp), so(b,sp)] = Dq*hcf[a,b]
    # Full 2-body V_{abcd}=<ab|1/r|cd> with spin deltas
    V = np.zeros((N,N,N,N),complex)
    for a in range(5):
     for b in range(5):
      for c in range(5):
       for d in range(5):
        for s1 in range(2):
         for s2 in range(2):
          V[so(a,s1),so(b,s2),so(c,s1),so(d,s2)] = Vm[a,b,c,d]
    # basis: pairs i<j
    basis = list(itertools.combinations(range(N),2))
    idx = {b:i for i,b in enumerate(basis)}
    D=len(basis)
    H=np.zeros((D,D),complex)
    def apply(ops, state):  # ops list of (type,orb) applied right-to-left: ops[-1] applied first
        st = list(state); sign=1
        for typ,o in reversed(ops):
            if typ=='c':   # creation
                if o in st: return None,0
                # insert at sorted position; sign = (-1)^{number of occupied below}
                n = sum(1 for x in st if x<o); sign *= (-1)**n
                st = sorted(st+[o])
            else:
                if o not in st: return None,0
                n = sum(1 for x in st if x<o); sign *= (-1)**n
                st.remove(o)
        return tuple(st), sign
    for J,(i,j) in enumerate(basis):
        st=(i,j)
        # one-body
        for a in range(N):
            for b in range(N):
                if h[a,b]!=0:
                    r,s = apply([('c',a),('a',b)], st)
                    if r is not None and len(r)==2:
                        H[idx[r],J] += h[a,b]*s
        # two-body 1/2 sum V_abcd a+_a a+_b a_d a_c
        for a in range(N):
         for b in range(N):
          for c in range(N):
           for d in range(N):
            v=V[a,b,c,d]
            if abs(v)<1e-12: continue
            r,s = apply([('c',a),('c',b),('a',d),('a',c)], st)
            if r is not None and len(r)==2:
                H[idx[r],J] += 0.5*v*s
    return H, basis
if __name__=="__main__":
    H,basis = build(0.0, 1.0)
    # Sz=+1 sector: both spin up -> indices so(m,0)=even
    ev = np.linalg.eigvalsh(H)
    print(np.round(ev,6))
EOF
cd /w && python3 d2.py