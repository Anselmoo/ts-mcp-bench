
cat << 'EOF' > /tmp/d5.py
import numpy as np, itertools
from scipy.special import lpmv, factorial
from math import pi, sqrt
B,C=621.0,2851.0
F2=49*B+7*C; F4=441*C/35.0
Fk={0:0.0,2:F2,4:F4}
# quadrature grid
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=40
phis=np.arange(nphi)*2*pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij')
W=np.outer(wg,np.ones(nphi))*(2*pi/nphi)
def Ylm(l,m,th,ph):
    am=abs(m)
    norm=sqrt((2*l+1)/(4*pi)*factorial(l-am)/factorial(l+am))
    return norm*lpmv(am,l,np.cos(th))*np.exp(1j*m*ph) if m>=0 else \
        ((-1)**am)*norm*lpmv(am,l,np.cos(th))*np.exp(1j*m*ph)
ms=list(range(-2,3))
Ym={m:Ylm(2,m,TH,PH) for m in ms}
# complex-basis Coulomb tensor
Vc=np.zeros((5,5,5,5),complex)
for k in (2,4):
    for q in range(-k,k+1):
        Ykq=Ylm(k,q,TH,PH)
        A=np.array([[np.sum(W*np.conj(Ym[m1])*np.conj(Ykq)*Ym[m3]) for m3 in ms] for m1 in ms])
        Bm=np.array([[np.sum(W*np.conj(Ym[m2])*Ykq*Ym[m4]) for m4 in ms] for m2 in ms])
        Vc+= Fk[k]*4*pi/(2*k+1)*np.einsum('ac,bd->abcd',A,Bm)
# real cubic-type orbitals (unnormalized angular functions)
x=np.sin(TH)*np.cos(PH); y=np.sin(TH)*np.sin(PH); z=np.cos(TH)
funcs=[x*y, x*z, y*z, x*x-y*y, 2*z*z-x*x-y*y]  # t2g: xy,xz,yz ; eg: x2-y2, z2
U=np.zeros((5,5),complex)
for i,f in enumerate(funcs):
    nrm=np.sqrt(np.sum(W*f*f))
    for j,m in enumerate(ms):
        U[i,j]=np.sum(W*np.conj(Ym[m])*f)/nrm
# check orthonormality
print("U U^dag:",np.round(U@U.conj().T,6).real.diagonal())
# real-basis Coulomb
Vr=np.einsum('ia,jb,kc,ld,abcd->ijkl',np.conj(U),np.conj(U),U,U,Vc,optimize=True)
eps_t2g=[0,1,2]; 
def build(Dq):
    eps=np.array([-4*Dq]*3+[6*Dq]*2)  # orbitals: 0,1,2 t2g; 3,4 eg
    # spin orbitals: idx=2*orb+s, s=0 up,1 down
    n=10
    states=[sum(1<<i for i in c) for c in itertools.combinations(range(n),5)]
    idx={s:i for i,s in enumerate(states)}
    def cre(st,i):
        if st>>i &1: return 0,None
        sgn=(-1)**bin(st & ((1<<i)-1)).count('1')
        return sgn, st|(1<<i)
    def ann(st,i):
        if not (st>>i &1): return 0,None
        sgn=(-1)**bin(st & ((1<<i)-1)).count('1')
        return sgn, st&~(1<<i)
    N=len(states)
    H=np.zeros((N,N))
    # spin-orbital two-electron integrals
    def Vso(a,b,c,d):
        oa,sa=a//2,a%2; ob,sb=b//2,b%2; oc,sc=c//2,c%2; od,sd=d//2,d%2
        if sa!=sc or sb!=sd: return 0.0
        return Vr[oa,ob,oc,od].real
    nz=[(a,b,c,d,Vso(a,b,c,d)) for a in range(n) for b in range(n) for c in range(n) for d in range(n)]
    nz=[t for t in nz if abs(t[4])>1e-9]
    for st in states:
        j=idx[st]
        H[j,j]+=sum(eps[i//2] for i in range(n) if st>>i&1)
        for a,b,c,d,v in nz:
            s1,t=ann(st,c)
            if not s1: continue
            s2,t=ann(t,d)
            if not s2: continue
            s3,t=cre(t,b)
            if not s3: continue
            s4,t=cre(t,a)
            if not s4: continue
            H[idx[t],j]+=0.5*v*s1*s2*s3*s4
    # S+ 
    Sp=np.zeros((N,N))
    for st in states:
        for o in range(5):
            up,dn=2*o,2*o+1
            s1,t=ann(st,dn)
            if not s1: continue
            s2,t=cre(t,up)
            if not s2: continue
            Sp[idx[t],idx[st]]+=s1*s2
    Sz=np.array([ (sum(1 for o in range(5) if st>>(2*o)&1)-sum(1 for o in range(5) if st>>(2*o+1)&1))/2 for st in states])
    return states,H,Sp,Sz
def energies(Dq):
    states,H,Sp,Sz=build(Dq)
    S2=Sp.T@Sp+np.diag(Sz*(Sz+1))  # S-S+ + Sz^2+Sz  with S- = Sp^T
    # sextet: all five up
    up5=states.index(sum(1<<(2*o) for o in range(5)))
    E6=H[up5,up5]
    sec=[i for i in range(len(states)) if abs(Sz[i]-0.5)<1e-9]
    Hs=H[np.ix_(sec,sec)]; S2s=S2[np.ix_(sec,sec)]
    w,v=np.linalg.eigh(S2s)
    sel=v[:,np.abs(w-0.75)<0.1]
    Hd=sel.T@Hs@sel
    Ed=np.linalg.eigvalsh(Hd).min()
    # check quartet/doublet counts
    return E6,Ed
for D in [0,1000,2000,3000]:
    print(D,energies(D))
from scipy.optimize import brentq
f=lambda D: (lambda e: e[0]-e[1])(energies(D))
xs=np.linspace(500,5000,19)
vals=[f(x) for x in xs]
print(list(zip(xs,np.round(vals,1))))
EOF
python3 /tmp/d5.py
