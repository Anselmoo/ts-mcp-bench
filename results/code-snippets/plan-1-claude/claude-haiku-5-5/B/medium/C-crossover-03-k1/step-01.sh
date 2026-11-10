
cat << 'EOF' > /tmp/d6.py
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import brentq
B,C=803.0,3078.0
F2=49*B+7*C; F4=35*0.0+C*441/35
# orbital m: -2..2 ; spin-orbitals index: (m,s), s=0 up,1 down
ms=[-2,-1,0,1,2]
# quadrature on sphere
nt,nph=60,120
x,w=np.polynomial.legendre.leggauss(nt)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*2*np.pi/nph
def Y(l,m,T,P): return sph_harm(m,l,P,T)  # scipy: sph_harm(m,n,azimuth,polar)
def ang(l1,m1,l2,m2,k,q,):  # int conj(Y_l1m1) Y_kq conj? helper not used
    pass
# one-body cubic potential v = Y40 + sqrt(10/7)(Y44+Y4-4)
v = Y(4,0,TH,PH) + np.sqrt(10/7)*(Y(4,4,TH,PH)+Y(4,-4,TH,PH))
M=np.zeros((5,5),complex)
for i,mi in enumerate(ms):
    for j,mj in enumerate(ms):
        M[i,j]=np.sum(W*np.conj(Y(2,mi,TH,PH))*v*Y(2,mj,TH,PH))
M=(M+M.conj().T)/2
ev,U=np.linalg.eigh(M)
print("raw eig",np.round(ev,6))
# eg doublet = two highest-magnitude same-valued pair; determine
# find doublet: eigenvalues with multiplicity 2
lam_e = ev[0] if abs(ev[0]-ev[1])<1e-8 else ev[3]
H1 = M*(6.0/lam_e)   # Dq=1 scaling: eg=+6, t2g=-4
print("check eig (per Dq):",np.round(np.linalg.eigvalsh(H1),6))
# two-body Coulomb angular integrals
def ang_k(k):
    # A[k][a,b,c,d] = 4pi/(2k+1) sum_q int conj(phi_a) phi_b Y*_kq  * int conj(phi_c) phi_d Y_kq   -> used as V=sum F^k * A
    A=np.zeros((5,5,5,5),complex)
    for q in range(-k,k+1):
        Ykq=Y(k,q,TH,PH)
        # f1[a,b] = int conj(phi_a) phi_b conj(Y_kq)
        f1=np.zeros((5,5),complex); f2=np.zeros((5,5),complex)
        for a,ma in enumerate(ms):
            for b,mb in enumerate(ms):
                pa=np.conj(Y(2,ma,TH,PH))*Y(2,mb,TH,PH)
                f1[a,b]=np.sum(W*pa*np.conj(Ykq))
                f2[a,b]=np.sum(W*pa*Ykq)
        # V(1,2) = sum_q Y*_kq(1) Y_kq(2): pair (a,b)=(i,k) electron1 ; (c,d)=(j,l) electron2
        A+= np.einsum('ab,cd->abcd',f1,f2)
    return 4*np.pi/(2*k+1)*A
A2=ang_k(2); A4=ang_k(4)
# V_{ijkl} = <i j|V| k l> with i,k electron1 orbitals, j,l electron2
# A[k][a,b,c,d]: a=i (conj), b=k (phi), c=j (conj), d=l
Vorb = F2*np.einsum('abcd->abcd',A2)+F4*A4
# Vorb[i,k,j,l] where indices: conj(phi_i) phi_k for e1 ; conj(phi_j) phi_l for e2
# Build spin-orbital one- and two-body in Fock space
nso=10
def idx(m,s): return ms.index(m)*2+s
def cdag_op(p):
    # Jordan-Wigner on 10 modes
    dim=2**nso; op=np.zeros((dim,dim))
    for st in range(dim):
        if not (st>>p)&1:
            sign=(-1)**bin(st & ((1<<p)-1)).count('1')
            op[st|(1<<p),st]=sign
    return op
Cd=[cdag_op(p) for p in range(nso)]
Cs=[c.T for c in Cd]
dim=2**nso
Nop=sum(Cd[p]@Cs[p] for p in range(nso))
Sz=sum(0.5*(Cd[idx(m,0)]@Cs[idx(m,0)]-Cd[idx(m,1)]@Cs[idx(m,1)]) for m in ms)
Sp=sum(Cd[idx(m,0)]@Cs[idx(m,1)] for m in ms)
Sm=Sp.T
S2=Sm@Sp+Sz@Sz+Sz
# two-body
Vee=np.zeros((dim,dim))
Hee=np.zeros((dim,dim))
for i,mi in enumerate(ms):
  for k,mk in enumerate(ms):
    for j,mj in enumerate(ms):
      for l,ml in enumerate(ms):
        val=Vorb[i,k,j,l]
        if abs(val)<1e-12: continue
        for si in range(2):
          for sk in range(2):
            if si!=sk: continue
            for sj in range(2):
              for sl in range(2):
                if sj!=sl: continue
                p=idx(mi,si); q=idx(mj,sj)
                r=idx(ml,sl); s=idx(mk,sk)
                # 1/2 sum V a+_p a+_q a_r a_s
                Hee+=0.5*val*(Cd[p]@Cd[q]@Cs[r]@Cs[s])
# one-body H1 per Dq
h1=np.zeros((dim,dim))
for a,ma in enumerate(ms):
  for b,mb in enumerate(ms):
    if abs(H1[a,b])<1e-12: continue
    for s in range(2):
      h1+=H1[a,b].real*(Cd[idx(ma,s)]@Cs[idx(mb,s)])
# restrict to N=6
keep=[st for st in range(dim) if bin(st).count('1')==6]
def sub(X): return X[np.ix_(keep,keep)]
Hee6=sub(Hee); h16=sub(h1); S26=sub(S2); Sz6=sub(Sz)
Mz=np.diag(sub(Sz)).round(3)
def sector(Ms2):
    # indices where Sz=Ms2/2
    ii=[n for n,st in enumerate(keep) if abs(np.diag(Sz6)[n]-Ms2/2)<1e-9]
    return ii
def E_quintet(Dq):
    H=Dq*h16+Hee6
    ii=sector(4)
    return np.linalg.eigvalsh(H[np.ix_(ii,ii)])[0]
def E_singlet(Dq):
    H=Dq*h16+Hee6
    ii=sector(0)
    Hs=H[np.ix_(ii,ii)]+1e6*S26[np.ix_(ii,ii)]
    ev=np.linalg.eigvalsh(Hs)
    return ev[0]
def E_ground_hs(Dq): return E_quintet(Dq)
for Dq in [0,1000,2000,2500,3000,3500]:
    print(Dq, E_quintet(Dq), E_singlet(Dq))
f=lambda d: E_singlet(d)-E_quintet(d)
r=brentq(f,1000,6000)
print("crossover Dq =",r, " E=",E_quintet(r))
EOF
python3 /tmp/d6.py
