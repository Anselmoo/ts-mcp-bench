cd /tmp && cat << 'EOF' | python3 -
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
nt, npp = 40, 80
x,w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(npp)*2*np.pi/npp
TH,PH = np.meshgrid(th,ph,indexing='ij'); W = np.outer(w, np.ones(npp))*(2*np.pi/npp)
Y=lambda l,m: sph_harm_y(l,m,TH,PH)
ms=[-2,-1,0,1,2]; Ys={m:Y(2,m) for m in ms}
integ=lambda f: np.sum(f*W)
X=np.sin(TH)*np.cos(PH); Yy=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
V = X**4+Yy**4+Z**4-0.6
Vm=np.array([[integ(np.conj(Ys[m])*V*Ys[mp]) for mp in ms] for m in ms]).real
Vsc=Vm*(6.0/np.linalg.eigvalsh(Vm)[3:].mean())
so=[(m,s) for m in ms for s in (0,1)]; n=10
ang={}
for k in (0,2,4):
    Yk={q:Y(k,q) for q in range(-k,k+1)}
    for a in ms:
        for c in ms:
            Ac={q: integ(np.conj(Ys[a])*np.conj(Yk[q])*Ys[c]) for q in Yk}
            for b in ms:
                for d in ms:
                    Bd={q: integ(np.conj(Ys[b])*Yk[q]*Ys[d]) for q in Yk}
                    ang[(k,a,c,b,d)]=4*np.pi/(2*k+1)*sum(Ac[q]*Bd[q] for q in Yk)
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
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0; F={0:0.0,2:F2,4:F4}
    dets=[d for d in itertools.combinations(range(n),8) if sum(1 if so[i][1]==0 else -1 for i in d)==Ms2]
    idx={d:i for i,d in enumerate(dets)}; H=np.zeros((len(dets),)*2)
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
                if r and r[1] in idx: H[idx[r[1]],col]+=r[0]*h[q,p]
        for k in d:
            for l in d:
                if k==l: continue
                for i in range(n):
                    for j in range(n):
                        if i==j: continue
                        v=Vint(i,j,k,l,F)
                        if abs(v)<1e-15: continue
                        r=apply_2(d,i,j,k,l)
                        if r and r[1] in idx: H[idx[r[1]],col]+=0.5*r[0]*v
    return H
def spec(Dq,B,C):
    e1=np.sort(np.linalg.eigvalsh(ham(Dq,B,C,2))); e0=list(np.sort(np.linalg.eigvalsh(ham(Dq,B,C,0))))
    for t in e1: e0.pop(int(np.argmin([abs(r-t) for r in e0])))
    return e1,np.array(e0)
def cl(e,tol=1e-3):
    out=[]
    for v in e:
        if out and abs(v-out[-1][0])<tol: out[-1][1]+=1
        else: out.append([v,1])
    return out
def pred(Dq,B,C):
    e1,s=spec(Dq,B,C); tr=[v for v,c in cl(e1)]; gs=e1[0]
    sE=[v for v,c in cl(s) if c==2]
    return np.array([tr[1]-gs,tr[2]-gs,tr[3]-gs,sE[0]-gs])
obs=np.array([9770,16050,26740,12987.])
Dq=977.0
r=least_squares(lambda p: pred(Dq,*p)[1:]-obs[1:], [900,3500], x_scale=[100,300])
print("Dq=977 fixed: B,C=",np.round(r.x,1)); print("pred",np.round(pred(Dq,*r.x),0)); print("obs ",obs)
EOF