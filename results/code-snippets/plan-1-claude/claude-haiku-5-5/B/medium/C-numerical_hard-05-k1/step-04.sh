python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm
nt, nphi = 24, 48
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.ones(nphi))*(2*np.pi/nphi)
def Y(l,m): return sph_harm(m, l, PH, TH)
ms=list(range(-2,3))
Ylm={m:Y(2,m) for m in ms}
def integ(f): return np.sum(W*f)
cache={}
def G(m1,m3,k,q):
    return integ(np.conj(Ylm[m1])*np.conj(Y(k,q))*Ylm[m3])
def H(m2,m4,k,q):
    return integ(np.conj(Ylm[m2])*Y(k,q)*Ylm[m4])
# precompute angular coefficients A[k][a,b,c,d]
def angular(k):
    A=np.zeros((5,5,5,5),complex)
    for a,b,c,d in itertools.product(range(5),repeat=4):
        s=0
        for q in range(-k,k+1):
            s+=G(ms[a],ms[c],k,q)*H(ms[b],ms[d],k,q)
        A[a,b,c,d]=4*np.pi/(2*k+1)*s
    return A
A2=angular(2); A4=angular(4)
# check: k=0 sanity skipped
F2=80.5; F4=0.70435*F2   # units of B
Vt=F2*A2+F4*A4
# one-electron
def ket(m): return np.eye(5)[m+2].astype(complex)
t2g=[ket(1),ket(-1),(ket(2)-ket(-2))/(1j*np.sqrt(2))]
eg=[ket(0),(ket(2)+ket(-2))/np.sqrt(2)]
P_t=sum(np.outer(v,v.conj()) for v in t2g); P_e=sum(np.outer(v,v.conj()) for v in eg)
n=10
dets=[sum(1<<i for i in c) for c in itertools.combinations(range(n),6)]
idx={d:k for k,d in enumerate(dets)}
def apply(state, ops):
    s=state; sign=1
    for typ,i in ops:
        occ=(s>>i)&1
        if typ=='a' and not occ: return None,0
        if typ=='c' and occ: return None,0
        sign*=(-1)**bin(s&((1<<i)-1)).count('1')
        s^=(1<<i)
    return s,sign
def spin(i): return i&1
def build(Dq):
    h=-4*Dq*P_t+6*Dq*P_e
    D=len(dets); Hm=np.zeros((D,D),complex)
    for col,d in enumerate(dets):
        for i in range(n):
            for j in range(n):
                oi,si=divmod(i,2); oj,sj=divmod(j,2)
                if si!=sj or h[oi,oj]==0: continue
                s,sg=apply(d,[('a',j),('c',i)])
                if s is not None: Hm[idx[s],col]+=h[oi,oj]*sg
        occ=[i for i in range(n) if (d>>i)&1]
        for k in occ:
            for l in occ:
                if k==l: continue
                pass
        for i,j,k,l in itertools.product(range(n),repeat=4):
            ok_,sk=divmod(k,2); ol,sl=divmod(l,2); oi,si=divmod(i,2); oj,sj=divmod(j,2)
            if si!=sk or sj!=sl: continue
            v=0.5*Vt[oi,oj,ok_,ol]
            if abs(v)<1e-14: continue
            s,sg=apply(d,[('a',k),('a',l),('c',j),('c',i)])
            if s is not None: Hm[idx[s],col]+=v*sg
    return Hm
Hfull=None
import time
t=time.time()
Hm=build(0.0)
print("built",time.time()-t, np.allclose(Hm,Hm.conj().T))
EOF