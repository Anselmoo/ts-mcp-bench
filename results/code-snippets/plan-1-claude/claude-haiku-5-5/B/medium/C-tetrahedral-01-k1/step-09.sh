cd /; cat << 'EOF' | python3 -
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import brentq, least_squares
def sph(m,l,PH,TH): return sph_harm_y(l,m,TH,PH)
nt, nph = 120, 240
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.linspace(0, 2*np.pi, nph, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.full(nph, 2*np.pi/nph))
rhat = np.stack([np.sin(TH)*np.cos(PH), np.sin(TH)*np.sin(PH), np.cos(TH)], -1)
ms=list(range(-2,3)); Y={m:sph(m,2,PH,TH) for m in ms}
lig=np.array([[1,1,1],[1,-1,-1],[-1,1,-1],[-1,-1,1]])/np.sqrt(3)
Vang=np.zeros((5,5),complex)
for L in lig:
    f=1.0/np.linalg.norm(rhat-L,axis=-1)
    for i,a in enumerate(ms):
        for j,b in enumerate(ms):
            Vang[i,j]+=np.sum(W*np.conj(Y[a])*f*Y[b])
ev=np.linalg.eigvalsh(Vang)
Vn=Vang*(10.0/(ev[2:].mean()-ev[:2].mean())); Vn=Vn-np.eye(5)*np.trace(Vn).real/5
print("Vn eig", np.round(np.linalg.eigvalsh(Vn),3))
def Vtensor(k):
    V=np.zeros((5,5,5,5),complex); pref=4*np.pi/(2*k+1)
    for q in range(-k,k+1):
        Ykq=sph(q,k,PH,TH)
        P=np.array([[np.sum(W*np.conj(Y[a])*np.conj(Ykq)*Y[c]) for c in ms] for a in ms])
        Q=np.array([[np.sum(W*np.conj(Y[a])*Ykq*Y[c]) for c in ms] for a in ms])
        V+=pref*np.einsum('ac,bd->abcd',P,Q)
    return V.real
V2=Vtensor(2); V4=Vtensor(4)
ORB=[(m,s) for m in ms for s in (0,1)]; n=10
def gtensor(V):
    g=np.zeros((n,n,n,n))
    for a,(ma,sa) in enumerate(ORB):
        for b,(mb,sb) in enumerate(ORB):
            for c,(mc,sc) in enumerate(ORB):
                for d,(md,sd) in enumerate(ORB):
                    if sa==sc and sb==sd: g[a,b,c,d]=V[ma+2,mb+2,mc+2,md+2]
    return g
G2=gtensor(V2); G4=gtensor(V4)
dets=[tuple(sorted(c)) for c in itertools.combinations(range(n),7)]
dets=[d for d in dets if sum(1 for o in d if o%2==0)==5]
idx={d:i for i,d in enumerate(dets)}; N=len(dets)
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
    M=np.zeros((N,N))
    for I,st in enumerate(dets):
        for a,b,c,d in itertools.product(range(n),repeat=4):
            if G[a,b,c,d]==0: continue
            new,sg=apply(st,[('c',a),('c',b),('a',d),('a',c)])
            if new is not None and new in idx: M[idx[new],I]+=0.5*sg*G[a,b,c,d]
    return M
def one_e(hm):
    M=np.zeros((N,N))
    for I,st in enumerate(dets):
        for p,q in itertools.product(range(n),repeat=2):
            if hm[p,q]==0: continue
            new,sg=apply(st,[('c',p),('a',q)])
            if new is not None and new in idx: M[idx[new],I]+=sg*hm[p,q]
    return M
hm=np.zeros((n,n))
for i,(m,s) in enumerate(ORB):
    for j,(m2,s2) in enumerate(ORB):
        if s==s2: hm[i,j]=Vn[m+2,m2+2].real
HL=one_e(hm); K2=two_e(G2); K4=two_e(G4)
def levels(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9
    e=np.sort(np.linalg.eigvalsh(Dq*HL+F2*K2+F4*K4))
    out=[]
    for v in e:
        if not out or v-out[-1][-1]>60: out.append([v])
        else: out[-1].append(v)
    return np.array([np.mean(g) for g in out])
obs=np.array([4070,7030,16400.])
def res(p):
    Dq,B=p
    L=levels(Dq,B,4*B)
    return (L[1:4]-L[0])-obs
print("levels Dq=407,B=800:", np.round(levels(407,800,3200)-levels(407,800,3200)[0],0))
sol=least_squares(res,[407,800],x_scale=[10,50])
print("fit (C=4B):",sol.x, "resid", np.round(res(sol.x),1))
# also fit with C free (3 params, 3 data) for check
def res3(p):
    Dq,B,C=p
    L=levels(Dq,B,C); return (L[1:4]-L[0])-obs
s3=least_squares(res3,[407,800,3200],x_scale=[10,50,200])
print("fit (C free):",s3.x,"resid",np.round(res3(s3.x),1))
EOF