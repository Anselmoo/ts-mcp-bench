import numpy as np, itertools
from scipy.special import sph_harm_y
def sph_harm(m, l, azim, polar): return sph_harm_y(l, m, polar, azim)
xg, wg = np.polynomial.legendre.leggauss(24)
nphi = 48
phis = np.arange(nphi)*2*np.pi/nphi
ct, ph = np.meshgrid(xg, phis, indexing='ij')
W = (np.repeat(wg[:,None], nphi, axis=1)*(2*np.pi/nphi)).ravel()
ct = ct.ravel(); ph = ph.ravel()
st = np.sqrt(1-ct**2)
X, Y, Z = st*np.cos(ph), st*np.sin(ph), ct
TH = np.arccos(ct)
ms = list(range(-2,3))
Yd = {m: sph_harm(m,2,ph,TH) for m in ms}
def proj_matrix(funcs):
    F = np.array(funcs).T
    Ginv = np.linalg.inv(F.conj().T @ (W[:,None]*F))
    B = np.array([Yd[m] for m in ms]).T
    PB = F @ (Ginv @ (F.conj().T @ (W[:,None]*B)))
    return B.conj().T @ (W[:,None]*PB)
h1 = -4*proj_matrix([X*Y,X*Z,Y*Z]) + 6*proj_matrix([X**2-Y**2, 3*Z**2-1.0+0j])
print("h1 eigen:", np.round(np.linalg.eigvalsh(h1),6))
K=[0,2,4]
A={k: np.zeros((5,5,5,5),dtype=complex) for k in K}
for k in K:
    Yk={q: sph_harm(q,k,ph,TH) for q in range(-k,k+1)}
    for a,b,c,d in itertools.product(range(5),repeat=4):
        s=0
        for q in range(-k,k+1):
            s += np.sum(W*np.conj(Yd[ms[a]])*Yd[ms[c]]*np.conj(Yk[q]))*np.sum(W*np.conj(Yd[ms[b]])*Yd[ms[d]]*Yk[q])
        A[k][a,b,c,d]=4*np.pi/(2*k+1)*s
# Slater integrals check: F0 coefficient should be 1 on diagonal (a=b=c=d)
print("A0[0,0,0,0] (should be 1):", A[0][0,0,0,0].real, " A2 diag:", A[2][0,0,0,0].real)
N=10
def build_basis(nup,ndn):
    st_=[]
    for ou in itertools.combinations(range(5),nup):
        for od in itertools.combinations(range(5),ndn):
            s=0
            for o in ou: s|=1<<(2*o)
            for o in od: s|=1<<(2*o+1)
            st_.append(s)
    return st_
def sgn(s,i): return (-1)**bin(s&((1<<i)-1)).count('1')
basis=build_basis(4,1); idx={s:i for i,s in enumerate(basis)}; D=len(basis)
def op_1body(h):
    H=np.zeros((D,D))
    for j,s in enumerate(basis):
        for p in range(N):
            for q in range(N):
                if p%2!=q%2: continue
                hv=h[p//2,q//2].real
                if abs(hv)<1e-14 or not (s>>q)&1: continue
                s1=s^(1<<q); sg=sgn(s,q)
                if (s1>>p)&1: continue
                sg*=sgn(s1,p); H[idx[s1|(1<<p)],j]+=sg*hv
    return H
def op_2body(F):
    H=np.zeros((D,D))
    for j,s in enumerate(basis):
        for c in range(N):
            if not (s>>c)&1: continue
            s1=s^(1<<c); sg1=sgn(s,c)
            for d in range(N):
                if d==c or not (s1>>d)&1: continue
                s2=s1^(1<<d); sg2=sg1*sgn(s1,d)
                for b in range(N):
                    if (s2>>b)&1 or b%2!=d%2: continue
                    s3=s2|(1<<b); sg3=sg2*sgn(s2,b)
                    for a in range(N):
                        if (s3>>a)&1 or a%2!=c%2: continue
                        v=sum(F[k]*A[k][a//2,b//2,c//2,d//2] for k in K).real
                        if abs(v)<1e-14: continue
                        H[idx[s3|(1<<a)],j]+=0.5*sg3*sgn(s3,a)*v
    return H
H1=op_1body(h1); H2=op_2body({0:0,2:1.0,4:0}); H4=op_2body({0:0,2:0,4:1.0})
# Check Hermiticity and free-ion 4G pure
Hf = lambda Dq,B,C: Dq*H1+(49*B+7*C)*H2+(63*C/5)*H4
w0,v0=np.linalg.eigh(Hf(0,1,0))
print("free ion B only levels:", np.unique(np.round(w0-w0[0],4), return_counts=True))
# G-subspace: 4G energy 10B+5C
B,C=245.71428571,4160.57142857
w0,v0=np.linalg.eigh(Hf(0,B,C))
G=[i for i in range(D) if abs(w0[i]-w0[0]-(10*B+5*C))<1e-6]
print("G subspace dim:", len(G))
PG=v0[:,G]@v0[:,G].T
w,v=np.linalg.eigh(Hf(643.75220599,B,C))
for i in range(D):
    print(f"E={w[i]-w[0]:10.2f}  Gfrac={v[:,i]@PG@v[:,i]:.3f}")
