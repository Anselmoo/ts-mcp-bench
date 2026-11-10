
mkdir -p ~/work && cd ~/work && cat << 'EOF' > d8.py
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
Vsc = Vm*(6.0/ev[3:].mean())   # eg=+6, t2g=-4 (Dq=1)
print("eig Vsc:",np.round(np.linalg.eigvalsh(Vsc),6))
so=[(m,s) for m in ms for s in (0,1)]  # s=0 up, 1 down
n=10
# angular integrals: Gk[k][(a,c,b,d)] for <ab|cd>: A_k = int Y_a^* Y_kq^* Y_c * int Y_b^* Y_kq Y_d
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
    # <i j | k l> with electron1: i*(orb) k ; electron2: j* l
    (mi,si),(mj,sj),(mk,sk),(ml,sl)=so[i],so[j],so[k],so[l]
    if si!=sk or sj!=sl: return 0.0
    return sum(F[kk]*ang[(kk,mi,mk,mj,ml)] for kk in (0,2,4)).real
def apply_ops(state, i,j,k,l,F):
    pass
def ham(Dq,B,C,Ms2):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    F={0:0.0,2:F2,4:F4}
    # determinant basis
    dets=[d for d in itertools.combinations(range(n),8) if sum(1 if so[i][1]==0 else -1 for i in d)==Ms2]
    idx={d:i for i,d in enumerate(dets)}
    N=len(dets); H=np.zeros((N,N))
    h=np.zeros((n,n))
    for i,(mi,si) in enumerate(so):
        for j,(mj,sj) in enumerate(so):
            if si==sj: h[i,j]=Dq*Vsc[ms.index(mi),ms.index(mj)]
    def apply_cdag_c(occ, p, q):
        # a_q^+ a_p on occupation list (sorted tuple) -> (sign, newtuple) or None
        occ=list(occ)
        if p not in occ: return None
        s=(-1)**sum(1 for x in occ if x<p); occ.remove(p)
        if q in occ: return None
        s*=(-1)**sum(1 for x in occ if x<q); occ.append(q)
        return s, tuple(sorted(occ))
    def apply_2(occ,i,j,k,l):
        # a_i^+ a_j^+ a_l a_k  acting on occ
        r=apply_cdag_c(occ,k,l) if False else None
        occ=list(occ)
        # annihilate k then l
        if k not in occ: return None
        s1=(-1)**sum(1 for x in occ if x<k); occ.remove(k)
        if l not in occ: return None
        s2=(-1)**sum(1 for x in occ if x<l); occ.remove(l)
        # create j then i
        if j in occ: return None
        s3=(-1)**sum(1 for x in occ if x<j); occ.append(j)
        if i in occ: return None
        s4=(-1)**sum(1 for x in occ if x<i); occ.append(i)
        return s1*s2*s3*s4, tuple(sorted(occ))
    for d in dets:
        col=idx[d]
        for p in d:
            for q in range(n):
                if h[q,p]==0: continue
                r=apply_cdag_c(d,p,q)
                if r is None: continue
                s,t=r
                if t in idx: H[idx[t],col]+=s*h[q,p]
        # two-body: 1/2 sum <ij|kl> a_i^+ a_j^+ a_l a_k
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
def levels(Dq,B,C):
    H1,_=ham(Dq,B,C,2)   # Ms=1 sector (n_up-n_down=2 -> sum=2)
    H0,d0=ham(Dq,B,C,0)
    e1=np.sort(np.linalg.eigvalsh(H1))
    e0=np.linalg.eigvalsh(H0)
    return e1,np.sort(e0)
if __name__=="__main__":
    e1,e0=levels(1.0,0.0,0.0)
    print(np.round(e1,4)); print(np.round(e0,4))
EOF
python3 d8.py