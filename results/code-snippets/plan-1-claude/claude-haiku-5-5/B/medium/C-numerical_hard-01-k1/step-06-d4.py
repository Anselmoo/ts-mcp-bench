import numpy as np, itertools
from scipy.special import sph_harm
nt, nphi = 40, 80
xg, wg = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*np.pi/nphi
ct, ph = np.meshgrid(xg, phis, indexing='ij')
W = np.outer(wg, np.ones(nphi))*(2*np.pi/nphi)
st = np.sqrt(1-ct**2)
X = st*np.cos(ph); Y = st*np.sin(ph); Z = ct
s15=np.sqrt(15); s5=np.sqrt(5)
real_orb = [s15/2*X*Y, s15/2*X*Z, s15/2*Y*Z, s15/4*(X**2-Y**2), s5/4*(3*Z**2-1)]
def ylm(k,q):
    return sph_harm(q, k, ph, np.arccos(ct))
def M(a,c,k,q):
    return np.sum(W*real_orb[a]*real_orb[c]*np.conj(ylm(k,q)))
ang = {}
for k in (0,2,4):
    Mt = {(a,c,q):M(a,c,k,q) for a in range(5) for c in range(5) for q in range(-k,k+1)}
    T = np.zeros((5,5,5,5))
    for a,c,b,d in itertools.product(range(5),repeat=4):
        T[a,c,b,d] = (4*np.pi/(2*k+1))*sum(Mt[a,c,q]*np.conj(Mt[b,d,q]) for q in range(-k,k+1))
    ang[k]=T.real
for a in range(5):
    assert abs(np.sum(W*real_orb[a]**2)-1)<1e-8, a
A2,A4 = ang[2], ang[4]
def build(Dq, B=1.0, CB=4.7):
    F4 = 441*CB*B/35; F2 = (441*B+5*F4)/9
    V = np.zeros((10,10,10,10))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        g = F2*A2[a,b,c,d] + F4*A4[a,b,c,d]
        if abs(g)<1e-12: continue
        for sa,sb,sc,sd in itertools.product(range(2),repeat=4):
            if sa==sc and sb==sd:
                V[2*a+sa,2*b+sb,2*c+sc,2*d+sd] += g
    h = np.zeros(10)
    for o in range(5):
        e = -4*Dq if o<3 else 6*Dq
        h[2*o]=h[2*o+1]=e
    states = [sum(1<<i for i in comb) for comb in itertools.combinations(range(10),4)]
    idx = {s:i for i,s in enumerate(states)}
    N=len(states); H=np.zeros((N,N))
    def ann(i,s):
        if not (s>>i)&1: return None,0
        return s & ~(1<<i), (-1)**bin(s & ((1<<i)-1)).count('1')
    def cre(i,s):
        if (s>>i)&1: return None,0
        return s | (1<<i), (-1)**bin(s & ((1<<i)-1)).count('1')
    quads = [(a,b,c,d,V[a,b,c,d]) for a,b,c,d in itertools.product(range(10),repeat=4) if abs(V[a,b,c,d])>1e-12 and a!=b and c!=d]
    for j,s in enumerate(states):
        for i in range(10):
            if (s>>i)&1: H[j,j]+=h[i]
        for a,b,c,d,v in quads:
            t,s1 = ann(c,s)
            if t is None: continue
            t,s2 = ann(d,t)
            if t is None: continue
            t,s3 = cre(b,t)
            if t is None: continue
            t,s4 = cre(a,t)
            if t is None: continue
            H[idx[t],j] += 0.5*v*s1*s2*s3*s4
    def sz_op(i): return 0.5 if i%2==0 else -0.5
    Sp = np.zeros((N,N)); Sm=np.zeros((N,N)); Sz=np.zeros((N,N))
    for j,s in enumerate(states):
        for o in range(5):
            up,dn = 2*o,2*o+1
            t,s1=ann(dn,s)
            if t is not None:
                t,s2=cre(up,t)
                if t is not None: Sp[idx[t],j]+=s1*s2
            t,s1=ann(up,s)
            if t is not None:
                t,s2=cre(dn,t)
                if t is not None: Sm[idx[t],j]+=s1*s2
        Sz[j,j] = sum(sz_op(i) for i in range(10) if (s>>i)&1)
    S2 = Sz@Sz + 0.5*(Sp@Sm + Sm@Sp)
    return states, H, S2
