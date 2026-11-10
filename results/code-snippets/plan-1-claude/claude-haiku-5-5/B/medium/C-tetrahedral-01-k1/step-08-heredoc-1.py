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
    f = 1.0/np.linalg.norm(rhat-L,axis=-1)
    for i,a in enumerate(ms):
        for j,b in enumerate(ms):
            Vang[i,j] += np.sum(W*np.conj(Y[a])*f*Y[b])
ev = np.linalg.eigvalsh(Vang)
Vn = Vang*(10.0/(ev[2:].mean()-ev[:2].mean()))
Vn = Vn - np.eye(5)*np.trace(Vn).real/5
# Coulomb angular: <ab|1/r12|cd> = sum_k F^k 4pi/(2k+1) sum_q P[a,c,q] Q[b,d,q],
# P[a,c,q]=∫ a* Y_kq* c ,  Q[b,d,q]=∫ b* Y_kq d
def PQ(k):
    Pd={}; Qd={}
    for q in range(-k,k+1):
        Ykq = sph(q,k,PH,TH)
        P=np.zeros((5,5),complex); Q=np.zeros((5,5),complex)
        for i,a in enumerate(ms):
            for j,c in enumerate(ms):
                P[i,j]=np.sum(W*np.conj(Y[a])*np.conj(Ykq)*Y[c])
                Q[i,j]=np.sum(W*np.conj(Y[a])*Ykq*Y[c])
        Pd[q]=P; Qd[q]=Q
    return Pd,Qd
def Vtensor(k):
    V=np.zeros((5,5,5,5),complex)
    Pd,Qd=PQ(k)
    pref=4*np.pi/(2*k+1)
    for q in range(-k,k+1):
        V+=pref*np.einsum('ac,bd->abcd',Pd[q],Qd[q])
    return V
V0=Vtensor(0)
V2=Vtensor(2); V4=Vtensor(4)
print("imag max V2", np.abs(V2.imag).max(), "V2 vs real", np.abs(V2-V2.real).max())
V2=V2.real; V4=V4.real
ORB=[(m,s) for m in ms for s in (0,1)]
n=10
def gtensor(V):
    g=np.zeros((n,n,n,n))
    for a,(ma,sa) in enumerate(ORB):
        for b,(mb,sb) in enumerate(ORB):
            for c,(mc,sc) in enumerate(ORB):
                for d,(md,sd) in enumerate(ORB):
                    if sa==sc and sb==sd: g[a,b,c,d]=V[ma+2,mb+2,mc+2,md+2]
    return g
G2=gtensor(V2); G4=gtensor(V4); G0=gtensor(V0.real)
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
HL=one_e(hm); K2=two_e(G2); K4=two_e(G4); K0=two_e(G0)
print("herm checks", np.abs(K2-K2.T).max(), np.abs(K4-K4.T).max())
# Check free-ion: F2=1,F4=0 spectrum
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
print("Dq=0,B=1000 levels rel:", np.round(levels(0,1000)-levels(0,1000)[0],1))
print("all eig Dq=0 B=1000:", np.round(np.linalg.eigvalsh(H(0,1000,4000))-np.linalg.eigvalsh(H(0,1000,4000))[0],1))
obs=np.array([4070,7030,16400.])
def res(p):
    Dq,B=p
    L=levels(Dq,B)
    if len(L)<4: return np.ones(3)*1e6
    return (L[1:4]-L[0])-obs
for g in [(400,700),(700,800)]:
    L=levels(*g); print(g, np.round(np.linalg.eigvalsh(H(*g,4*g[1]))-np.linalg.eigvalsh(H(*g,4*g[1]))[0],0))
sol=least_squares(res,[500,800],x_scale=[100,100])
print("fit Dq,B:",sol.x, "resid", res(sol.x))
