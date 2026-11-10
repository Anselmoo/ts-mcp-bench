cat << 'EOF' > ~/d7run.py
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
nt, nphi = 30, 60
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.full(nphi, 2*np.pi/nphi))
X=np.sin(TH)*np.cos(PH); Yc=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
raw=[X*Yc, Yc*Z, X*Z, X**2-Yc**2, 3*Z**2-1]
vals=np.array([v/np.sqrt(np.sum(W*v*v)) for v in raw])
def ang(k,a,b,c,d):
    s=0
    for q in range(-k,k+1):
        Yk=np.conj(sph_harm_y(k,q,TH,PH))
        s+= np.sum(W*a*c*Yk)*np.conj(np.sum(W*b*d*Yk))
    return 4*np.pi/(2*k+1)*s
A={}
for k in (0,2,4):
    A[k]=np.zeros((5,5,5,5))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        A[k][a,b,c,d]=np.real(ang(k,vals[a],vals[b],vals[c],vals[d]))
N=10
def occ_ms(s):
    up=sum(1 for o in range(5) if s>>(2*o)&1); dn=sum(1 for o in range(5) if s>>(2*o+1)&1)
    return up-dn
states=[sum(1<<i for i in c) for c in itertools.combinations(range(N),7)]
sts=[s for s in states if occ_ms(s)==3]   # Ms=3/2 (up-down = 3 with 7 e: 5 up,2 down)
idx={s:i for i,s in enumerate(sts)}
def apply_ann(s,i):
    if not (s>>i)&1: return None,0
    return s^(1<<i), (-1)**bin(s&((1<<i)-1)).count('1')
def apply_cre(s,i):
    if (s>>i)&1: return None,0
    return s|(1<<i), (-1)**bin(s&((1<<i)-1)).count('1')
# precompute two-body (spin-orbital) integrals per k
def Vint(k,i,j,kk,l):
    oi,si=divmod(i,2); oj,sj=divmod(j,2); ok,sk=divmod(kk,2); ol,sl=divmod(l,2)
    if si!=sk or sj!=sl: return 0.0
    return A[k][oi,oj,ok,ol]
# build operator matrices for pieces: one-body h (diag per real orbital) ; two-body parts
def build_pieces():
    # one-body matrix elements for each orbital pair (real basis, spin diagonal) -> we use occupation-number basis
    # Coulomb matrix per k
    Hk={k:np.zeros((len(sts),len(sts))) for k in (0,2,4)}
    Hcf={}
    for s in sts:
        col=idx[s]
        for k in (0,2,4):
            for i,j,kk,l in itertools.product(range(N),repeat=4):
                if i==j or kk==l: continue
                v=Vint(k,i,j,kk,l)
                if abs(v)<1e-14: continue
                s1,g1=apply_ann(s,kk)
                if s1 is None: continue
                s2,g2=apply_ann(s1,l)
                if s2 is None: continue
                s3,g3=apply_cre(s2,j)
                if s3 is None: continue
                s4,g4=apply_cre(s3,i)
                if s4 is None: continue
                if s4 in idx: Hk[k][idx[s4],col]+=0.5*v*g1*g2*g3*g4
    # one-body operator n_orb-diagonal pieces: build separately for each real orbital (diagonal in real basis)
    Hcf=np.zeros((5,len(sts),len(sts)))  # Hcf[o] = number operator for real orbital o (both spins)
    for s in sts:
        col=idx[s]
        for o in range(5):
            n=((s>>(2*o))&1)+((s>>(2*o+1))&1)
            Hcf[o,col,col]=n
    return Hk,Hcf
Hk,Hcf=build_pieces()
def H(Dq,B,C):
    F4=C*441/35.0; F2=(441*B+5*F4)/9.0
    Hc=F2*Hk[2]+F4*Hk[4]     # F0 term constant for fixed config? include F0 separately (irrelevant)
    h=np.array([-4*Dq,-4*Dq,-4*Dq,6*Dq,6*Dq])
    Hcf_tot=sum(h[o]*Hcf[o] for o in range(5))
    return Hc+Hcf_tot
# check Dq=0 spectrum
ev=np.linalg.eigvalsh(H(0,1000,0.0))
print("Dq=0,B=1000,C=0 quartet levels (F/P split):",np.round(ev,2))
EOF
python3 ~/d7run.py