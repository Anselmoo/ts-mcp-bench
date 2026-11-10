import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares

nt, nph = 80, 160
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.linspace(0, 2*np.pi, nph, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.full(nph, 2*np.pi/nph))
rhat = np.stack([np.sin(TH)*np.cos(PH), np.sin(TH)*np.sin(PH), np.cos(TH)], -1)
ms = list(range(-2,3))
Y = {m: sph_harm(m,2,PH,TH) for m in ms}
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
        Ykq = sph_harm(q,k,PH,TH)
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
# Sector: Ms=3/2 -> 5 up (even idx) 2 down (odd idx)
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
def opmat(terms2, ops_list):
    pass
# Build one-electron ops matrices L[p,q] (in sector) and two-electron K(G)
def one_e_mats():
    M={}
    for p in range(n):
        for q in range(n):
            Mat=np.zeros((N,N))
            for I,st in enumerate(dets):
                new,sg=apply(st,[('c',p),('a',q)])
                if new is not None and new in idx: Mat[idx[new],I]+=sg
            M[(p,q)]=Mat
    return M
def two_e(G):
    Mat=np.zeros((N,N))
    for I,st in enumerate(dets):
        for a in range(n):
            for b in range(n):
                for c in range(n):
                    for d in range(n):
                        if G[a,b,c,d]==0: continue
                        new,sg=apply(st,[('c',a),('c',b),('a',d),('a',c)])
                        if new is not None: Mat[idx[new],I]+=0.5*sg*G[a,b,c,d]
    return Mat
# ligand-field one-electron matrix in spin-orbital basis
Hl_orb=np.zeros((n,n))
for i,(m,s) in enumerate(ORB):
    for j,(m2,s2) in enumerate(ORB):
        if s==s2: Hl_orb[i,j]=Vn[m+2,m2+2].real
E1=one_e_mats()
HL=np.zeros((N,N))
for p in range(n):
    for q in range(n):
        if Hl_orb[p,q]!=0: HL+=Hl_orb[p,q]*E1[(p,q)]
K2=two_e(G2); K4=two_e(G4)
np.savez('/dev/null') if False else None
# F2,F4 from Racah B,C with C=4B: F4=441C/35, F2=(441B+5F4)/9
def H(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9
    return Dq*HL + F2*K2 + F4*K4
def levels(Dq,B,C):
    return np.linalg.eigvalsh(H(Dq,B,C))
e=levels(0,1000,4000)
print("sector dim",N)
print("ground-check (B=1000,Dq=0)", np.round(np.unique(np.round(e,3))[:6],2))
np.save('/dev/null',0) if False else None
import pickle
pickle.dump((HL,K2,K4),open('/root/mats.pkl','wb')) if False else None
globals_out=(HL,K2,K4)
# store for fitting
def residuals(p, obs, C_ratio=4.0):
    Dq,B = p
    C = C_ratio*B
    ev=np.unique(np.round(levels(Dq,B,C),3))
    # distinct levels: [4A2, 4T2, 4T1F, 4T1P] assumed ordering
    return None
import sys
np.set_printoptions(suppress=True, linewidth=150)
def distinct(ev,tol=0.5):
    out=[]
    for v in ev:
        if not out or abs(v-out[-1])>tol: out.append(v)
    return np.array(out)
def trans(Dq,B,C=None):
    if C is None: C=4*B
    d=distinct(levels(Dq,B,C))
    return d-d[0]
for Dq,B in [(400,700),(500,800)]:
    print(Dq,B, np.round(trans(Dq,B),1))
