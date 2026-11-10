import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares
# quadrature on sphere
nt, np_ = 60, 120
x,w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(np_)*2*np.pi/np_
TH,PH = np.meshgrid(th,ph,indexing='ij'); W = np.outer(w, np.ones(np_))*(2*np.pi/np_)
def Y(l,m,T,P): return sph_harm(m,l,P,T)  # scipy: sph_harm(m,n,azimuth,polar)
ms=[-2,-1,0,1,2]
Ys={m:Y(2,m,TH,PH) for m in ms}
def integ(f): return np.sum(f*W)
# cubic potential on unit sphere
X=np.sin(TH)*np.cos(PH); Yc=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
V = X**4+Yc**4+Z**4-0.6
Vm = np.array([[integ(np.conj(Ys[m])*V*Ys[mp]) for mp in ms] for m in ms])
ev = np.linalg.eigvalsh(Vm)
print("cubic eigen (unnormalized):", np.round(ev,5))
# t2g are lower (-), eg higher: eg = top two
eg_ = ev[3:]; t2_=ev[:3]
scale = 10.0/(eg_.mean()-t2_.mean())  # Dq = 1 unit => eg +6, t2g -4
# Vm_scaled so that eg=+6Dq, t2g=-4Dq with Dq=1
Vsc = Vm*(6.0/eg_.mean())
print("check eg,t2g:", np.round(np.linalg.eigvalsh(Vsc),4))
# two-electron angular factors
R=np.array([[integ(np.conj(Ys[a])*Ys[b]*0+0) for b in ms] for a in ms])
def Ang(k,q,a,b):  # int Y_a^* Y_{k q}^* Y_b  (complex Y_kq)
    Ykq = Y(k,q,TH,PH)
    return integ(np.conj(Ys[a])*np.conj(Ykq)*Ys[b])
# spin-orbitals: (m, s), s=+1/2 idx0, -1/2 idx1
so=[(m,s) for m in ms for s in (0,1)]
n=len(so)
# precompute ang coefficients G[k][(a,c)][q] = int Y_a^* Y_kq^* Y_c
Gk={}
for k in (0,2,4):
    for a in ms:
        for c in ms:
            for q in range(-k,k+1):
                Gk[(k,a,c,q)] = Ang(k,q,a,c)
def eri(i,j,kk,l,F):
    # <ij|kk l> = sum_k F^k 4pi/(2k+1) sum_q [int phi_i^* Y_kq^* phi_kk][int phi_j^* Y_kq phi_l]
    (mi,si),(mj,sj),(mk,sk),(ml,sl)=so[i],so[j],so[kk],so[l]
    if si!=sk or sj!=sl: return 0.0
    tot=0.0
    for k in (0,2,4):
        if F[k]==0: continue
        s=0.0
        for q in range(-k,k+1):
            # int phi_i^* Y_kq^* phi_k  and int phi_j^* Y_{kq} phi_l
            # Y_kq^* conj, then second uses Y_kq (conj of Y_{k,-q} with sign) -> compute directly
            Ykq=Y(k,q,TH,PH)
            A=integ(np.conj(Ys[mi])*np.conj(Ykq)*Ys[mk])
            Bq=integ(np.conj(Ys[mj])*Ykq*Ys[ml])
            s+=A*Bq
        tot+=F[k]*4*np.pi/(2*k+1)*s.real
    return tot
def build(Dq,B,C,sector_Ms):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    F={0:0.0,2:F2,4:F4}
    # Ms sector basis
    dets=[]
    for occ in itertools.combinations(range(n),8):
        Ms2=sum(1 if so[i][1]==0 else -1 for i in occ)
        if Ms2==sector_Ms: dets.append(occ)
    idx={d:i for i,d in enumerate(dets)}
    N=len(dets); H=np.zeros((N,N))
    # precompute one-electron matrix in spin orbital basis
    h=np.zeros((n,n))
    for i,(mi,si) in enumerate(so):
        for j,(mj,sj) in enumerate(so):
            if si==sj: h[i,j]=Dq*Vsc[ms.index(mi),ms.index(mj)].real
    # E-E: build with generic formula: H = sum h_ij a_i^+ a_j + 1/2 sum V_ijkl a_i^+ a_j^+ a_l a_k
    # eri cache
    Vc={}
    def V(i,j,k,l):
        key=(i,j,k,l)
        if key not in Vc: Vc[key]=eri(i,j,k,l,F)
        return Vc[key]
    for d in dets:
        occ=list(d); occset=set(d)
        col=idx[d]
        # one-electron
        for p in occ:
            for q in range(n):
                if abs(h[q,p])<1e-14: continue
                # a_q^+ a_p
                if q!=p and q in occset: continue
                newocc = [x for x in occ if x!=p]
                sign=(-1)**sum(1 for x in occ if x<p)
                if q!=p:
                    sign2=(-1)**sum(1 for x in newocc if x<q)
                    sign*=sign2
                    newocc2=sorted(newocc+[q])
                else:
                    newocc2=sorted(newocc+[q]); sign*=1
                t=tuple(newocc2)
                if t in idx: H[idx[t],col]+=sign*h[q,p]
        # two-electron: 1/2 sum V_ijkl a_i^+ a_j^+ a_l a_k
        for a_ in occ:
            for b_ in occ:
                if a_==b_: continue
                for c_ in range(n):
                    for d_ in range(n):
                        pass
    return H, dets, idx, F, V
