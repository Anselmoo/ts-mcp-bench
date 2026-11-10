cd /tmp && cat << 'EOF' | python3 -
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares
nt, npp = 40, 80
x,w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(npp)*2*np.pi/npp
TH,PH = np.meshgrid(th,ph,indexing='ij'); W = np.outer(w, np.ones(npp))*(2*np.pi/npp)
def Y(l,m): return sph_harm(m,l,PH,TH)
ms=[-2,-1,0,1,2]
Ys={m:Y(2,m) for m in ms}
integ=lambda f: np.sum(f*W)
X=np.sin(TH)*np.cos(PH); Yy=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
V = X**4+Yy**4+Z**4-0.6
Vm = np.array([[integ(np.conj(Ys[m])*V*Ys[mp]) for mp in ms] for m in ms]).real
ev=np.linalg.eigvalsh(Vm)
Vsc = Vm*(6.0/ev[3:].mean())
print("eig Vsc:",np.round(np.linalg.eigvalsh(Vsc),6))
so=[(m,s) for m in ms for s in (0,1)]
n=10
ang={}
for k in (0,2,4):
    Yk={q:Y(k,q) for q in range(-k,k+1)}
    for a in ms:
        for c in ms:
            Ac={q: integ(np.conj(Ys[a])*np.conj(Yk[q])*Ys[c]) for q in Yk}
            for b in ms:
                for d in ms:
                    Bd={q: integ(np.conj(Ys[b])*Yk[q]*Ys[d]) for q in Yk}
                    ang[(k,a,c,b,d)] = 4*np.pi/(2*k+1)*sum(Ac[q]*Bd[q] for q in Yk)
def Vint(i,j,k,l,F):
    (mi,si),(mj,sj),(mk,sk),(ml,sl)=so[i],so[j],so[k],so[l]
    if si!=sk or sj!=sl: return 0.0
    return sum(F[kk]*ang[(kk,mi,mk,mj,ml)] for kk in (0,2,4)).real
def apply_2(occ,i,j,k,l):
    occ=list(occ)
    if k not in occ: return None
    s1=(-1)**sum(1 for x in occ if x<k); occ.remove(k)
    if l not in occ: return None
    s2=(-1)**sum(1 for x in occ if x<l); occ.remove(l)
    if j in occ: return None
    s3=(-1)**sum(1 for x in occ if x<j); occ.append(j)
    if i in occ: return None
    s4=(-1)**sum(1 for x in occ if x<i); occ.append(i)
    return s1*s2*s3*s4, tuple(sorted(occ))
def apply_1(occ,p,q):
    occ=list(occ)
    if p not in occ: return None
    s=(-1)**sum(1 for x in occ if x<p); occ.remove(p)
    if q in occ: return None
    s*=(-1)**sum(1 for x in occ if x<q); occ.append(q)
    return s, tuple(sorted(occ))
def ham(Dq,B,C,Ms2):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    F={0:0.0,2:F2,4:F4}
    dets=[d for d in itertools.combinations(range(n),8) if sum(1 if so[i][1]==0 else -1 for i in d)==Ms2]
    idx={d:i for i,d in enumerate(dets)}
    N=len(dets); H=np.zeros((N,N))
    h=np.zeros((n,n))
    for i,(mi,si) in enumerate(so):
        for j,(mj,sj) in enumerate(so):
            if si==sj: h[i,j]=Dq*Vsc[ms.index(mi),ms.index(mj)]
    for d in dets:
        col=idx[d]
        for p in range(n):
            for q in range(n):
                if h[q,p]==0: continue
                r=apply_1(d,p,q)
                if r is None: continue
                s,t=r
                if t in idx: H[idx[t],col]+=s*h[q,p]
        for k in d:
            for l in d:
                if k==l: continue
                for i in range(n):
                    for j in range(n):
                        if i==j: continue
                        v=Vint(i,j,k,l,F)
                        if v==0: continue
                        r=apply_2(d,i,j,k,l)
                        if r is None: continue
                        s,t=r
                        if t in idx: H[idx[t],col]+=0.5*s*v
    return H, dets
# sanity check: Ms2 in terms of sum of spin signs: up=+1
H1,_=ham(1.0,0,0,2); print("free-ion-free check Dq only, Ms=1 eig:", np.round(np.linalg.eigvalsh(H1),4))
EOF