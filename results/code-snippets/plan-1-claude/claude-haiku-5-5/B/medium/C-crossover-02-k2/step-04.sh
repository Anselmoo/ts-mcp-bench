cat << 'EOF' > /tmp/x 2>/dev/null; cat << 'EOF2' | python3 -
import numpy as np, itertools
from scipy.special import lpmv, factorial
from math import pi, sqrt
from scipy.optimize import brentq
B,C=621.0,2851.0
F2=49*B+7*C; F4=441*C/35.0
Fk={2:F2,4:F4}
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=40
phis=np.arange(nphi)*2*pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij')
W=np.outer(wg,np.ones(nphi))*(2*pi/nphi)
def Ylm(l,m,th,ph):
    am=abs(m)
    norm=sqrt((2*l+1)/(4*pi)*factorial(l-am)/factorial(l+am))
    val=norm*lpmv(am,l,np.cos(th))*np.exp(1j*am*ph)
    if m<0: val=((-1)**am)*np.conj(val)
    return val
ms=list(range(-2,3))
Ym={m:Ylm(2,m,TH,PH) for m in ms}
Vc=np.zeros((5,5,5,5),complex)
for k in (2,4):
    for q in range(-k,k+1):
        Ykq=Ylm(k,q,TH,PH)
        A=np.array([[np.sum(W*np.conj(Ym[m1])*np.conj(Ykq)*Ym[m3]) for m3 in ms] for m1 in ms])
        Bm=np.array([[np.sum(W*np.conj(Ym[m2])*Ykq*Ym[m4]) for m4 in ms] for m2 in ms])
        Vc+= Fk[k]*4*pi/(2*k+1)*np.einsum('ac,bd->abcd',A,Bm)
x=np.sin(TH)*np.cos(PH); y=np.sin(TH)*np.sin(PH); z=np.cos(TH)
funcs=[x*y, x*z, y*z, x*x-y*y, 2*z*z-x*x-y*y]
U=np.zeros((5,5),complex)
for i,f in enumerate(funcs):
    nrm=np.sqrt(np.sum(W*f*f))
    for j,m in enumerate(ms):
        U[i,j]=np.sum(W*np.conj(Ym[m])*f)/nrm
Vr=np.einsum('ia,jb,kc,ld,abcd->ijkl',np.conj(U),np.conj(U),U,U,Vc,optimize=True)
assert np.abs(Vr.imag).max()<1e-6
Vr=Vr.real
n=10
states=[sum(1<<i for i in c) for c in itertools.combinations(range(n),5)]
idx={s:i for i,s in enumerate(states)}
N=len(states)
def cre(st,i):
    if st>>i&1: return 0,None
    return (-1)**bin(st&((1<<i)-1)).count('1'), st|(1<<i)
def ann(st,i):
    if not st>>i&1: return 0,None
    return (-1)**bin(st&((1<<i)-1)).count('1'), st&~(1<<i)
def Vso(a,b,c,d):
    if a%2!=c%2 or b%2!=d%2: return 0.0
    return Vr[a//2,b//2,c//2,d//2]
nz=[(a,b,c,d,Vso(a,b,c,d)) for a in range(n) for b in range(n) for c in range(n) for d in range(n)]
nz=[t for t in nz if abs(t[4])>1e-9]
H2=np.zeros((N,N))
for st in states:
    j=idx[st]
    for a,b,c,d,v in nz:
        s1,t=ann(st,c)
        if not s1: continue
        s2,t=ann(t,d)
        if not s2: continue
        s3,t=cre(t,b)
        if not s3: continue
        s4,t=cre(t,a)
        if not s4: continue
        H2[idx[t],j]+=0.5*v*s1*s2*s3*s4
Sp=np.zeros((N,N))
for st in states:
    for o in range(5):
        s1,t=ann(st,2*o+1)
        if not s1: continue
        s2,t=cre(t,2*o)
        if not s2: continue
        Sp[idx[t],idx[st]]+=s1*s2
Sz=np.array([(sum(1 for o in range(5) if st>>(2*o)&1)-sum(1 for o in range(5) if st>>(2*o+1)&1))/2 for st in states])
occ=np.array([[st>>i&1 for i in range(n)] for st in states])
S2=Sp.T@Sp+np.diag(Sz*(Sz+1))
sec=[i for i in range(N) if abs(Sz[i]-0.5)<1e-9]
w,v=np.linalg.eigh(S2[np.ix_(sec,sec)])
sel=v[:,np.abs(w-0.75)<0.1]
print("doublet subspace dim",sel.shape[1])
up5=idx[sum(1<<(2*o) for o in range(5))]
def energies(Dq):
    eps=np.array([-4*Dq]*3+[6*Dq]*2)
    H=H2.copy()
    for j,st in enumerate(states):
        H[j,j]+=sum(eps[i//2] for i in range(n) if st>>i&1)
    E6=H[up5,up5]
    Hd=sel.T@H[np.ix_(sec,sec)]@sel
    return E6, np.linalg.eigvalsh(Hd).min()
for D in [0,1000,2000,3000]:
    print(D,energies(D))
f=lambda D: energies(D)[0]-energies(D)[1]
xs=np.linspace(500,6000,12)
print([round(f(x),1) for x in xs])
r=brentq(f,1000,4000,xtol=1e-6)
print("crossover Dq =",r, "Dq/B=",r/B)
EOF2