python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
B,C=803.0,3078.0
F4=441*C/35.0; F2=(441*B+5*F4)/9.0
Fk={0:0.0,2:F2,4:F4}
nth,nph=60,120
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*(2*np.pi/nph)
def Y(l,m): return sph_harm_y(l,m,TH,PH)
# sanity: orthonormality
print("norm", np.sum(W*np.abs(Y(2,1))**2))
ms=list(range(-2,3))
Yd={m:Y(2,m) for m in ms}
ang1={(k,q,m1,m3):np.sum(W*np.conj(Yd[m1])*np.conj(Y(k,q))*Yd[m3]) for k in (0,2,4) for q in range(-k,k+1) for m1 in ms for m3 in ms}
ang2={(k,q,m2,m4):np.sum(W*np.conj(Yd[m2])*Y(k,q)*Yd[m4]) for k in (0,2,4) for q in range(-k,k+1) for m2 in ms for m4 in ms}
Vsp={}
for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
    tot=0
    for k in (0,2,4):
        s=sum(ang1[(k,q,m1,m3)]*ang2[(k,q,m2,m4)] for q in range(-k,k+1))
        tot+=Fk[k]*4*np.pi/(2*k+1)*s
    Vsp[(m1,m2,m3,m4)]=tot.real
so=[(m,s) for m in ms for s in (0,1)]
N=10
Vt=np.zeros((N,N,N,N))
for a,b,c,d in itertools.product(range(N),repeat=4):
    ma,sa=so[a]; mb,sb=so[b]; mc,sc=so[c]; md,sd=so[d]
    if sa==sc and sb==sd: Vt[a,b,c,d]=Vsp[(ma,mb,mc,md)]
s2=1/np.sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
orbs={'xy':(vec({2:1j*s2,-2:-1j*s2}),-4),'yz':(vec({1:1j*s2,-1:1j*s2}),-4),
      'xz':(vec({1:-s2,-1:s2}),-4),'x2y2':(vec({2:s2,-2:s2}),6),'z2':(vec({0:1.0}),6)}
H1=np.zeros((5,5),complex)
for n,(v,e) in orbs.items(): H1+=e*np.outer(v,np.conj(v))
print("H1 trace", np.trace(H1).real, "herm", np.allclose(H1,H1.conj().T))
dets=[sum(1<<i for i in c) for c in itertools.combinations(range(N),6)]
idx={d:i for i,d in enumerate(dets)}
D=len(dets)
def par(x): return -1 if bin(x).count('1')%2 else 1
Hcf=np.zeros((D,D)); Hee=np.zeros((D,D))
hso={}
for i,(m,s) in enumerate(so):
    for j,(mp,sp) in enumerate(so):
        if s==sp and abs(H1[m+2,mp+2])>1e-14: hso[(i,j)]=H1[m+2,mp+2].real
nz=[(a,b,c,d,Vt[a,b,c,d]) for a,b,c,d in itertools.product(range(N),repeat=4) if abs(Vt[a,b,c,d])>1e-12 and a!=b and c!=d]
for col,st in enumerate(dets):
    for (p,q),val in hso.items():
        if not (st>>q)&1: continue
        sg=par(st & ((1<<q)-1)); t=st^(1<<q)
        if (t>>p)&1: continue
        sg*=par(t & ((1<<p)-1)); t|=(1<<p)
        Hcf[idx[t],col]+=sg*val
    for a,b,c,d,v in nz:
        if not (st>>c)&1: continue
        s1=par(st & ((1<<c)-1)); t=st^(1<<c)
        if not (t>>d)&1: continue
        s2_=par(t & ((1<<d)-1)); t^=(1<<d)
        if (t>>b)&1: continue
        s3=par(t & ((1<<b)-1)); t|=(1<<b)
        if (t>>a)&1: continue
        s4=par(t & ((1<<a)-1)); t|=(1<<a)
        Hee[idx[t],col]+=0.5*v*s1*s2_*s3*s4
print("herm ee", np.allclose(Hee,Hee.T), "herm cf", np.allclose(Hcf,Hcf.T))
# S+ and S2
Sp=np.zeros((D,D)); Sz=np.zeros(D)
for col,st in enumerate(dets):
    Sz[col]=0.5*sum((1 if so[i][1]==0 else -1) for i in range(N) if (st>>i)&1)
    for m in ms:
        up=2*(m+2); dn=up+1
        if (st>>dn)&1 and not (st>>up)&1:
            sg=par(st & ((1<<dn)-1)); t=st^(1<<dn)
            sg*=par(t & ((1<<up)-1)); t|=(1<<up)
            Sp[idx[t],col]+=sg
S2=Sp.T@Sp+np.diag(Sz*(Sz+1))
print("S2 eig", np.unique(np.round(np.linalg.eigvalsh(S2),6)))
def lowest(Dq):
    H=Hee+Dq*Hcf
    ev,evec=np.linalg.eigh(S2+0*np.eye(D))
    out={}
    for S in (0,2):
        P=evec[:,np.abs(ev-S*(S+1))<1e-6]
        out[S]=np.linalg.eigvalsh(P.T@H@P)[0]
    return out
# free ion check: ground energy relative
for Dq in [0,1000,2000,2500,3000]:
    r=lowest(Dq); print(Dq, r, "E1-E5", r[0]-r[2])
from scipy.optimize import brentq
f=lambda d: lowest(d)[0]-lowest(d)[2]
for lo,hi in [(0,40000)]:
    xs=np.linspace(lo,hi,81); vals=[f(v) for v in xs]
    for i in range(len(xs)-1):
        if vals[i]*vals[i+1]<0:
            r=brentq(f,xs[i],xs[i+1]); print("crossover Dq=",r,"Dq/B=",r/B)
EOF