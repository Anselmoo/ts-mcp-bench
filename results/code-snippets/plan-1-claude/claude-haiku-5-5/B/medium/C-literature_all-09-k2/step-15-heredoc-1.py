import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
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
K=[0,2,4]
A={k: np.zeros((5,5,5,5),dtype=complex) for k in K}
for k in K:
    Yk={q: sph_harm(q,k,ph,TH) for q in range(-k,k+1)}
    for a,b,c,d in itertools.product(range(5),repeat=4):
        s=0
        for q in range(-k,k+1):
            s += np.sum(W*np.conj(Yd[ms[a]])*Yd[ms[c]]*np.conj(Yk[q]))*np.sum(W*np.conj(Yd[ms[b]])*Yd[ms[d]]*Yk[q])
        A[k][a,b,c,d]=4*np.pi/(2*k+1)*s
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
np.save if False else None
def Hf(Dq,B,C): return Dq*H1+(49*B+7*C)*H2+(63*C/5)*H4

# Group levels (distinct eigenvalues relative to sextet) with multiplicity and G-character
def groups(Dq,B,C):
    w0,v0=np.linalg.eigh(Hf(0,B,C))
    G=[i for i in range(D) if abs(w0[i]-w0[0]-(10*B+5*C))<1e-6]
    PG=v0[:,G]@v0[:,G].T
    w,v=np.linalg.eigh(Hf(Dq,B,C))
    e=w[1:]-w[0]; vv=v[:,1:]
    out=[]
    for i in range(len(e)):
        g=vv[:,i]@PG@vv[:,i]
        if out and abs(e[i]-out[-1][0])<1e-6: out[-1][1]+=1; out[-1][2]+=g
        else: out.append([e[i],1,g])
    return out
# Observed
obs={'T1':19720.,'T2':23260.,'E':24980.}
# Physical expectation check: print groups at a trial
for g in groups(700,800,3500): print(f"  E={g[0]:9.1f} mult={g[1]} Gsum={g[2]:.3f}")
