mkdir -p /tmp/w && cd /tmp/w && cat > d2.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm

xg, wg = np.polynomial.legendre.leggauss(24)
phis = np.linspace(0, 2*np.pi, 48, endpoint=False); wp = 2*np.pi/48
TH, PH = np.meshgrid(np.arccos(xg), phis, indexing='ij')
W = np.outer(wg, np.full(len(phis), wp))
def Y(l, m): return sph_harm(m, l, PH, TH)
ms = list(range(-2, 3))
Yl = {m: Y(2, m) for m in ms}
def integ(f): return np.sum(W*f)

def ang(k):
    A = np.zeros((5,5,5,5), complex)
    for i1,m1 in enumerate(ms):
        for i3,m3 in enumerate(ms):
            for q in range(-k,k+1):
                Ykq = Y(k,q)
                a = integ(np.conj(Yl[m1])*Yl[m3]*np.conj(Ykq))
                for i2,m2 in enumerate(ms):
                    for i4,m4 in enumerate(ms):
                        b = integ(np.conj(Yl[m2])*Yl[m4]*Ykq)
                        A[i1,i2,i3,i4] += 4*np.pi/(2*k+1)*a*b
    return A
A = {k: ang(k) for k in (0,2,4)}

X = np.sin(TH)*np.cos(PH); Yc = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
t2fs = [X*Yc, Yc*Z, X*Z]
efs = [X**2-Yc**2, 3*Z**2-1]
def proj_vecs(fs):
    out=[]
    for f in fs:
        v = np.array([integ(np.conj(Yl[m])*f) for m in ms])
        for u in out: v = v - np.vdot(u,v)*u
        out.append(v/np.linalg.norm(v))
    return out
def proj(vecs):
    P=np.zeros((5,5),complex)
    for v in vecs: P += np.outer(np.conj(v), v)
    return P
Pt2 = proj(proj_vecs(t2fs)); Pe = proj(proj_vecs(efs))
print("trace Pt2,Pe:", np.trace(Pt2).real, np.trace(Pe).real)
hcf = -4*Pt2 + 6*Pe

def so(im, sp): return 2*im+sp
N=10
basis = list(itertools.combinations(range(N),2))
idx = {b:i for i,b in enumerate(basis)}

def apply(ops, state):
    st = list(state); sign=1
    for typ,o in reversed(ops):
        n = sum(1 for x in st if x<o)
        if typ=='c':
            if o in st: return None,0
            sign *= (-1)**n; st = sorted(st+[o])
        else:
            if o not in st: return None,0
            sign *= (-1)**n; st.remove(o)
    return tuple(st), sign

def build(Dq, Bv, Cv=None):
    if Cv is None: Cv = 4*Bv
    F4 = 441*Cv/35; F2 = (441*Bv+5*F4)/9
    Vm = F2*A[2] + F4*A[4]
    h = np.zeros((N,N),complex)
    for a in range(5):
        for b in range(5):
            for sp in range(2):
                h[so(a,sp), so(b,sp)] = Dq*hcf[a,b]
    V = np.zeros((N,N,N,N),complex)
    for a in range(5):
     for b in range(5):
      for c in range(5):
       for d in range(5):
        for s1 in range(2):
         for s2 in range(2):
          V[so(a,s1),so(b,s2),so(c,s1),so(d,s2)] = Vm[a,b,c,d]
    D=len(basis); H=np.zeros((D,D),complex)
    for J,st in enumerate(basis):
        for a in range(N):
            for b in range(N):
                if abs(h[a,b])>1e-12:
                    r,s = apply([('c',a),('a',b)], st)
                    if r is not None and len(r)==2: H[idx[r],J] += h[a,b]*s
        for a,b,c,d in itertools.product(range(N),repeat=4):
            v=V[a,b,c,d]
            if abs(v)<1e-12: continue
            r,s = apply([('c',a),('c',b),('a',d),('a',c)], st)
            if r is not None and len(r)==2: H[idx[r],J] += 0.5*v*s
    return H
EOF
cat > run1.py << 'EOF'
from d2 import *
H = build(0.0, 1.0)
print(np.round(np.linalg.eigvalsh(H),6))
EOF
timeout 500 python3 run1.py