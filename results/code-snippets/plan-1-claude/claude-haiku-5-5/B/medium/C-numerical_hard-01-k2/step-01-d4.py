import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares
from scipy.integrate import dblquad
# Angular quadrature (Gauss-Legendre x uniform phi)
nt, nphi = 40, 80
xg, wg = np.polynomial.legendre.leggauss(nt)
th = np.arccos(xg); ph = np.arange(nphi)*2*np.pi/nphi; wph = 2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = (wg[:,None]*wph*np.ones_like(TH))
ms = [-2,-1,0,1,2]
def Y(l,m,t,p): return sph_harm(m,l,p,t)   # scipy: sph_harm(m,n,azimuth,polar)
# angular coefficient a_k(ma,mc;mb,md) = sum_q <Y_la^* Y_kq^* Y_lc>... compute via integrals
def ang(k, ma, mc, mb, md):
    # integral of conj(Y_ma(1)) * conj(Y_mb(2)) * (4pi/(2k+1)) sum_q Y_kq(1)^* Y_kq(2)... general: 
    # V_{ab,cd} = sum_k F^k * 4pi/(2k+1) * sum_q <a|Y_kq*|c> <b|Y_kq|d>  (a,c on electron1; b,d on electron2)
    s=0
    for q in range(-k,k+1):
        A = np.sum(W*np.conj(Y(2,ma,TH,PH))*np.conj(Y(k,q,TH,PH))*Y(2,mc,TH,PH))
        B = np.sum(W*np.conj(Y(2,mb,TH,PH))*Y(k,q,TH,PH)*Y(2,md,TH,PH))
        s += A*B
    return 4*np.pi/(2*k+1)*s
# spin-orbitals: index (m, s), s=+1/2 -> 0, -1/2 -> 1 ; orbital index m+2
so = [(m,s) for m in ms for s in (0,1)]
N=len(so)
# two-electron integrals per k (in units of F^k)
V = {}
for k in (0,2,4):
    Vk = np.zeros((N,N,N,N),complex)
    for a,(ma,sa) in enumerate(so):
        for b,(mb,sb) in enumerate(so):
            for c,(mc,sc) in enumerate(so):
                for d,(md,sd) in enumerate(so):
                    if sa!=sc or sb!=sd: continue
                    Vk[a,b,c,d]=ang(k,ma,mc,mb,md)
    V[k]=Vk
# Slater-Condon: H_ee = 1/2 sum V_abcd c^+_a c^+_b c_d c_c  with V_abcd = sum_k F^k * ang_k(a,c;b,d) (electron1 a<-c, electron2 b<-d)
# Racah-type: F0 irrelevant (constant for fixed N). Use F2,F4 with F4 = ratio
def build(F2,F4):
    Vt = F2*V[2]+F4*V[4]
    dets = list(itertools.combinations(range(N),4))
    idx = {d:i for i,d in enumerate(dets)}
    return dets, idx, Vt
def apply_ee(det, Vt):
    out={}
    occ=list(det)
    for c in occ:
        for d in occ:
            pass
    return out
def ee_matrix(F2,F4):
    dets,idx,Vt = build(F2,F4)
    M=np.zeros((len(dets),len(dets)),complex)
    for j,dj in enumerate(dets):
        for a in range(N):
            for b in range(N):
                for c in range(N):
                    for d in range(N):
                        v=Vt[a,b,c,d]
                        if abs(v)<1e-12: continue
                        # operator 1/2 V_abcd a+_a a+_b a_d a_c   (a,b create; c,d annihilate)
                        # apply a_c then a_d then a+_b then a+_a
                        st=list(dj); sign=1
                        def ann(st,x,sign):
                            if x not in st: return None,0
                            p=st.index(x); s=(-1)**p
                            st=st[:p]+st[p+1:]; return st,sign*s
                        st2,s2=ann(st,c,sign)
                        if st2 is None: continue
                        st3,s3=ann(st2,d,s2)
                        if st3 is None: continue
                        # create b then a
                        if b in st3: continue
                        p=sum(1 for x in st3 if x<b); st4=sorted(st3+[b]); s4=s3*(-1)**p
                        if a in st4: continue
                        p=sum(1 for x in st4 if x<a); st5=tuple(sorted(st4+[a])); s5=s4*(-1)**p
                        if st5 in idx:
                            M[idx[st5],j]+=0.5*v*s5
    return M,dets
