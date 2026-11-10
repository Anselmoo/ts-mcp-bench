import numpy as np, itertools
from scipy.special import sph_harm
from scipy.linalg import eigh
from numpy.polynomial.legendre import leggauss
# angular grid
nt,nphi=40,80
x,w=leggauss(nt); th=np.arccos(x); ph=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=(np.outer(w,np.ones(nphi))*2*np.pi/nphi)
def Ylm(l,m,T,P): return sph_harm(m,l,P,T)   # scipy: sph_harm(m,n,azimuth,polar)
# real d orbitals (complex basis m=-2..2 orthonormal; use complex basis directly)
ms=[-2,-1,0,1,2]
orb={m:Ylm(2,m,TH,PH) for m in ms}
# angular coefficient a_k(m1 m2; m3 m4) = 4pi/(2k+1) sum_q <m1|Y_kq^*|m3><m2|Y_kq|m4>  (complex basis, integrals over sphere)
def ang(k,a,b,c,d):
    s=0
    for q in range(-k,k+1):
        Yk=Ylm(k,q,TH,PH)
        s+= np.sum(W*np.conj(orb[a])*np.conj(Yk)*orb[c]) * np.sum(W*np.conj(orb[b])*Yk*orb[d])
    return 4*np.pi/(2*k+1)*s
# Slater-Condon: V(ab|cd)= sum_k F^k a_k, with F0,F2,F4 (k=0,2,4) ; use F0=0
# single-particle basis: spin orbitals (m,s)
so=[(m,s) for m in ms for s in (0.5,-0.5)]
N=len(so)
# precompute angular coefficient tables for k=2,4
A={}
for k in (2,4):
    A[k]=np.zeros((5,5,5,5),complex)
    for i,a in enumerate(ms):
     for j,b in enumerate(ms):
      for l,c in enumerate(ms):
       for n,d in enumerate(ms):
        A[k][i,j,l,n]=ang(k,a,b,c,d)
# two-body operator in spin-orbital basis: <ab|V|cd> = delta_spin(a,c)delta_spin(b,d) * sum_k F^k a_k(ma mb; mc md)
def Vsp(F2,F4):
    V=np.zeros((N,N,N,N),complex)
    for i,(ma,sa) in enumerate(so):
     for j,(mb,sb) in enumerate(so):
      for l,(mc,sc) in enumerate(so):
       for n,(md,sd) in enumerate(so):
        if sa!=sc or sb!=sd: continue
        ia=ms.index(ma); ib=ms.index(mb); ic=ms.index(mc); idd=ms.index(md)
        V[i,j,l,n]=F2*A[2][ia,ib,ic,idd]+F4*A[4][ia,ib,ic,idd]
    return V
# determinants for 3 electrons
dets=list(itertools.combinations(range(N),3))
idx={d:i for i,d in enumerate(dets)}
def apply_cd(i,j,l,n,det):
    # c_i^dag c_j^dag c_l c_n acting on det (tuple sorted); return (sign,newdet) or None
    occ=list(det)
    sign=1
    # annihilate n then l (c_l c_n |det>)
    for op in (n,l):
        if op not in occ: return None
        p=occ.index(op); sign*= (-1)**p; occ.pop(p)
    # create j then i: c_j^dag then c_i^dag
    for op in (j,i):
        if op in occ: return None
        # insert in sorted position
        p=sum(1 for x in occ if x<op); sign*=(-1)**p; occ.insert(p,op)
    return sign,tuple(occ)
def H(F2,F4,Dq,B=None):
    V=Vsp(F2,F4)
    M=np.zeros((len(dets),len(dets)),complex)
    # one-body crystal field: eg (z2,x2-y2) +6Dq, t2g -4Dq
    def cf(m): return 6*Dq if abs(m)==2 or m==0 else -4*Dq
    # real basis not needed for diagonal in m? Dq operator is diagonal in complex m basis for cubic? Not generally; build numerically below
    # build one-electron Dq matrix in complex m basis via projection: Oh potential = -4Dq for t2g, +6Dq for eg. Use Y_4 cubic harmonic (diagonal in m only for tetragonal). Use numeric: potential V(theta,phi)
    return M,V
