import numpy as np, itertools
from scipy.special import sph_harm
nt, nph = 40, 80
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nph)*2*np.pi/nph
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.full(nph, 2*np.pi/nph))
X = np.sin(TH)*np.cos(PH); Y = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
funcs = {'xy':X*Y,'yz':Y*Z,'xz':X*Z,'x2y2':X**2-Y**2,'z2':3*Z**2-1}
names = list(funcs)
for n in names:
    f = funcs[n]; funcs[n] = f/np.sqrt(np.sum(W*f*f))
def ang_k(k):
    out = np.zeros((5,5,5,5),dtype=complex)
    for q in range(-k,k+1):
        Ykq = sph_harm(q, k, PH, TH)
        Ac = np.array([[np.sum(W*funcs[a]*np.conj(Ykq)*funcs[c]) for c in names] for a in names])
        Bd = np.array([[np.sum(W*funcs[b]*Ykq*funcs[d]) for d in names] for b in names])
        out += np.einsum('ac,bd->acbd', Ac, Bd)
    return (out*4*np.pi/(2*k+1)).real
A = {k: ang_k(k) for k in (0,2,4)}
N=10; ne=5
states=[sum(1<<i for i in c) for c in itertools.combinations(range(N),ne)]
idx={s:i for i,s in enumerate(states)}
def apply(ops,s):
    sg=1; cur=s
    for typ,o in ops:
        if typ=='a':
            if not (cur>>o)&1: return None
            sg*=(-1)**bin(cur&((1<<o)-1)).count('1'); cur^=(1<<o)
        else:
            if (cur>>o)&1: return None
            sg*=(-1)**bin(cur&((1<<o)-1)).count('1'); cur|=(1<<o)
    return sg,cur
so=lambda p,sp: 2*p+sp
def build(Dq,B,C):
    F4 = C*441/35; F2 = (441*B+5*F4)/9
    V = np.zeros((5,5,5,5))
    for k,Fk in ((2,F2),(4,F4)):
        V += Fk*np.einsum('acbd->abcd', A[k])
    h = np.diag([-4*Dq]*3+[6*Dq]*2)
    n=len(states); H=np.zeros((n,n))
    for si,s in enumerate(states):
        for p in range(5):
            for q in range(5):
                if h[p,q]!=0:
                    for sp in (0,1):
                        r=apply([('c',so(p,sp)),('a',so(q,sp))],s)
                        if r: H[idx[r[1]],si]+=h[p,q]*r[0]
        for p,q,r_,s_ in itertools.product(range(5),repeat=4):
            v=V[p,q,r_,s_]
            if abs(v)<1e-12: continue
            for s1 in (0,1):
                for s2 in (0,1):
                    r=apply([('a',so(r_,s1)),('a',so(s_,s2)),('c',so(q,s2)),('c',so(p,s1))],s)
                    if r: H[idx[r[1]],si]+=0.5*v*r[0]
    return H
# S^2
n=len(states); Sp=np.zeros((n,n)); Sz=np.zeros(n)
for si,s in enumerate(states):
    for o in range(5):
        r=apply([('c',2*o),('a',2*o+1)],s)
        if r: Sp[idx[r[1]],si]+=r[0]
    Sz[si]=0.5*sum(((s>>(2*o))&1)-((s>>(2*o+1))&1) for o in range(5))
S2 = Sp.T@Sp + np.diag(Sz*(Sz+1))   # S-S+ form, Sp = S+ (raises)
