cd /tmp && cat << 'EOF' | python3 -
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
nt, npp = 40, 80
x,w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(npp)*2*np.pi/npp
TH,PH = np.meshgrid(th,ph,indexing='ij'); W = np.outer(w, np.ones(npp))*(2*np.pi/npp)
def Y(l,m): return sph_harm_y(l,m,TH,PH)
ms=[-2,-1,0,1,2]
Ys={m:Y(2,m) for m in ms}
integ=lambda f: np.sum(f*W)
X=np.sin(TH)*np.cos(PH); Yy=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
V = X**4+Yy**4+Z**4-0.6
Vm = np.array([[integ(np.conj(Ys[m])*V*Ys[mp]) for mp in ms] for m in ms]).real
ev=np.linalg.eigvalsh(Vm)
Vsc = Vm*(6.0/ev[3:].mean())
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
                if abs(h[q,p])<1e-15: continue
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
                        if abs(v)<1e-15: continue
                        r=apply_2(d,i,j,k,l)
                        if r is None: continue
                        s,t=r
                        if t in idx: H[idx[t],col]+=0.5*s*v
    return H
def spectrum(Dq,B,C):
    e1=np.sort(np.linalg.eigvalsh(ham(Dq,B,C,2)))
    e0=np.sort(np.linalg.eigvalsh(ham(Dq,B,C,0)))
    # remove triplet eigenvalues (appear in Ms=0 too) : match
    trip=list(e1); singl=[]
    rem=list(e0)
    for t in trip:
        j=np.argmin([abs(r-t) for r in rem]); rem.pop(j)
    singl=np.array(rem)
    return e1, singl
def cluster(e,tol=1e-3):
    out=[]
    for v in e:
        if out and abs(v-out[-1][0])<tol: out[-1][1]+=1
        else: out.append([v,1])
    return out
e1,s=spectrum(1.0,0.0,0.0)
print("triplets",cluster(e1)); print("singlets",cluster(s))
# fit
obs={'3T2':9770,'3T1F':16050,'3T1P':26740,'1E':12987}
def model(p):
    Dq,B,C=p
    e1,s=spectrum(Dq,B,C)
    tr=cluster(e1); g=e1[0]
    T=[v for v,c in tr]
    T2=[v for v,c in tr if c==3]
    gs=e1[0]
    # triplet levels in order
    tl=[v for v,c in tr]
    sl=[v for v,c in cluster(s)]
    # singlet E: degeneracy 2
    sE=[v for v,c in cluster(s,1e-3) if c==2]
    return dict(T2=tl[1]-gs, T1F=tl[2]-gs, T1P=tl[3]-gs, E=sE[0]-gs, tr=tr, sing=cluster(s))
def res(p):
    m=model(p)
    return [m['T2']-9770, m['T1F']-16050, m['T1P']-26740, m['E']-12987]
for start in [(977,1000,4000),(1000,800,3500),(900,1100,4500)]:
    r=least_squares(res,start,x_scale=[100,100,300])
    m=model(r.x); print(np.round(r.x,1), np.round(r.fun,1), "T2 %.0f T1F %.0f T1P %.0f E %.0f"%(m['T2'],m['T1F'],m['T1P'],m['E']))
EOF