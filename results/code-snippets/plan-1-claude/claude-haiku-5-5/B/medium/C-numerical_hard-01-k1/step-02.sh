mkdir -p /w && cat > /w/d4.py <<'EOF'
import numpy as np, itertools
from scipy.special import sph_harm
# quadrature on sphere
nt, nphi = 40, 80
xg, wg = np.polynomial.legendre.leggauss(nt)   # x = cos(theta)
phis = np.arange(nphi)*2*np.pi/nphi
ct, ph = np.meshgrid(xg, phis, indexing='ij')
W = np.outer(wg, np.ones(nphi))*(2*np.pi/nphi)
st = np.sqrt(1-ct**2)
X = st*np.cos(ph); Y = st*np.sin(ph); Z = ct
s15=np.sqrt(15); s5=np.sqrt(5)
real_orb = [
 s15/2*X*Y,      # xy  t2g
 s15/2*X*Z,      # xz  t2g
 s15/2*Y*Z,      # yz  t2g
 s15/4*(X**2-Y**2), # x2-y2 eg
 s5/4*(3*Z**2-1)    # z2 eg
]
def ylm(k,q):
    # scipy sph_harm(m, n, azimuth, polar)
    return sph_harm(q, k, ph, np.arccos(ct))
def M(a,c,k,q):
    return np.sum(W*real_orb[a]*real_orb[c]*np.conj(ylm(k,q)))
ang = {}
for k in (0,2,4):
    for a,c,b,d in itertools.product(range(5),repeat=4):
        s=0
        for q in range(-k,k+1):
            s += M(a,c,k,q)*np.conj(M(b,d,k,q))
        ang.setdefault(k,np.zeros((5,5,5,5)))[a,c,b,d] = (4*np.pi/(2*k+1))*s
# check orthonormality
for a in range(5):
    assert abs(np.sum(W*real_orb[a]**2)-1)<1e-8, a
A0,A2,A4 = ang[0].real, ang[2].real, ang[4].real
def build(Dq, B=1.0, CB=4.7):
    F4 = 441*CB*B/35; F2 = (441*B+5*F4)/9
    # spin orbitals: idx = 2*orb+spin
    V = np.zeros((10,10,10,10))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        g = F2*A2[a,b,c,d] + F4*A4[a,b,c,d]   # F0 omitted (constant)
        if g==0: continue
        for sa,sb,sc,sd in itertools.product(range(2),repeat=4):
            if sa==sc and sb==sd:
                V[2*a+sa,2*b+sb,2*c+sc,2*d+sd] += g
    h = np.zeros(10)
    for o in range(5):
        e = -4*Dq if o<3 else 6*Dq
        h[2*o]=h[2*o+1]=e
    # Fock basis, 4 electrons in 10 spin orbitals
    states = [sum(1<<i for i in comb) for comb in itertools.combinations(range(10),4)]
    idx = {s:i for i,s in enumerate(states)}
    N=len(states); H=np.zeros((N,N))
    def apply_ann(i,s):
        if not (s>>i)&1: return None,0
        sign = (-1)**bin(s & ((1<<i)-1)).count('1')
        return s & ~(1<<i), sign
    def apply_cre(i,s):
        if (s>>i)&1: return None,0
        sign = (-1)**bin(s & ((1<<i)-1)).count('1')
        return s | (1<<i), sign
    for j,s in enumerate(states):
        # one-body
        for i in range(10):
            if (s>>i)&1: H[j,j]+=h[i]
        # two-body: 1/2 sum V_abcd a+_a a+_b a_d a_c
        for a,b,c,d in itertools.product(range(10),repeat=4):
            v = V[a,b,c,d]
            if v==0 or a==b or c==d: continue
            t,s1 = apply_ann(c,s)
            if t is None: continue
            t,s2 = apply_ann(d,t)
            if t is None: continue
            t,s3 = apply_cre(b,t)
            if t is None: continue
            t,s4 = apply_cre(a,t)
            if t is None: continue
            H[idx[t],j] += 0.5*v*s1*s2*s3*s4
    # S^2 via Sz and S+S-
    Sz = np.zeros((N,N)); S2=np.zeros((N,N))
    return states, H
EOF
cd /w && python3 -c "
import d4,numpy as np
st,H=d4.build(0.0)
print(H.shape, np.allclose(H,H.T))
"