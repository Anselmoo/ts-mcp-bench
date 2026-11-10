import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares

def sph(m,l,PH,TH): return sph_harm_y(l,m,TH,PH)
nt, nph = 80, 160
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.linspace(0, 2*np.pi, nph, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.full(nph, 2*np.pi/nph))
rhat = np.stack([np.sin(TH)*np.cos(PH), np.sin(TH)*np.sin(PH), np.cos(TH)], -1)
ms = list(range(-2,3))
Y = {m: sph(m,2,PH,TH) for m in ms}
lig = np.array([[1,1,1],[1,-1,-1],[-1,1,-1],[-1,-1,1]])/np.sqrt(3)
Vang = np.zeros((5,5),complex)
for L in lig:
    f = -1.0/np.linalg.norm(rhat-L,axis=-1)
    for i,a in enumerate(ms):
        for j,b in enumerate(ms):
            Vang[i,j] += np.sum(W*np.conj(Y[a])*f*Y[b])
ev = np.linalg.eigvalsh(Vang)
print("raw eig", np.round(ev,5))
Vn = Vang*(10.0/(ev[2:].mean()-ev[:2].mean()))
Vn = Vn - np.eye(5)*np.trace(Vn).real/5
print("Vn eig", np.round(np.linalg.eigvalsh(Vn),4))

def Pk(k):
    out={}
    for q in range(-k,k+1):
        Ykq = sph(q,k,PH,TH)
        M=np.zeros((5,5),complex)
        for i,a in enumerate(ms):
            for j,c in enumerate(ms):
                M[i,j]=np.sum(W*np.conj(Y[a])*np.conj(Ykq)*Y[c])
        out[q]=M
    return out
Pks={k:Pk(k) for k in (2,4)}
def Vtensor(k):
    V=np.zeros((5,5,5,5),complex)
    pref=4*np.pi/(2*k+1)
    for q in range(-k,k+1):
        P=Pks[k][q]
        V+=pref*np.einsum('ac,bd->abcd',P,P)
    return V.real
V2=Vtensor(2); V4=Vtensor(4)
ORB=[(m,s) for m in range(5) for s in (0,1)]
n=10
def gtensor(V):
    g=np.zeros((n,n,n,n))
    for a,(ma,sa) in enumerate(ORB):
        for b,(mb,sb) in enumerate(ORB):
            for c,(mc,sc) in enumerate(ORB):
                for d,(md,sd) in enumerate(ORB):
                    if sa==sc and sb==sd: g[a,b,c,d]=V[ma+2,mb+2,mc+2,md+2]
    return g
G2=gtensor(V2); G4=gtensor(V4)
# Ms=3/2 sector: 5 up (even index), 2 down (odd)
dets=[tuple(sorted(c)) for c in itertools.combinations(range(n),7)]
dets=[d for d in dets if sum(1 for o in d if o%2==0)==5]
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def apply(state,ops):
    occ=list(state); sign=1
    for typ,o in reversed(ops):
        if typ=='a':
            if o not in occ: return None,0
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None,0
            p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
    return tuple(occ),sign
def two_e(G):
    Mat=np.zeros((N,N))
    for I,st in enumerate(dets):
        for a,b,c,d in itertools.product(range(n),repeat=4):
            if G[a,b,c,d]==0: continue
            new,sg=apply(st,[('c',a),('c',b),('a',d),('a',c)])
            if new is not None and new in idx: Mat[idx[new],I]+=0.5*sg*G[a,b,c,d]
    return Mat
def one_e(hm):
    Mat=np.zeros((N,N))
    for I,st in enumerate(dets):
        for p,q in itertools.product(range(n),repeat=2):
            if hm[p,q]==0: continue
            new,sg=apply(st,[('c',p),('a',q)])
            if new is not None and new in idx: Mat[idx[new],I]+=sg*hm[p,q]
    return Mat
hm=np.zeros((n,n))
for i,(m,s) in enumerate(ORB):
    for j,(m2,s2) in enumerate(ORB):
        if s==s2: hm[i,j]=Vn[m+2,m2+2].real
HL=one_e(hm); K2=two_e(G2); K4=two_e(G4)
print("sector dim",N, "norms", np.abs(HL).sum(), np.abs(K2).sum(), np.abs(K4).sum())
np.savez('/root/mats.npz',HL=HL,K2=K2,K4=K4) if False else None

def H(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9
    return Dq*HL + F2*K2 + F4*K4
def distinct(ev,tol=0.5):
    out=[]
    for v in ev:
        if not out or abs(v-out[-1])>tol: out.append(v)
    return np.array(out)
def levels(Dq,B,C=None):
    if C is None: C=4*B
    return distinct(np.linalg.eigvalsh(H(Dq,B,C)))
# test: Dq=0 free ion quartet levels relative
print("free-ion (B=1000):", np.round(levels(0,1000)-levels(0,1000)[0],1))
np.set_printoptions(suppress=True, linewidth=150)
obs=np.array([4070,7030,16400.])
def res(p):
    Dq,B=p
    L=levels(Dq,B)
    if len(L)<4: return np.ones(3)*1e6
    t=L[1:4]-L[0]
    return t-obs
for g in [(400,700),(700,800),(900,900),(600,1000)]:
    print(g, np.round(levels(*g)-levels(*g)[0],0))
sol=least_squares(res,[700,800],x_scale=[100,100])
print("fit Dq,B:",sol.x, "resid", res(sol.x))
