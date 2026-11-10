import numpy as np, itertools
from scipy.special import sph_harm
B,C=803.0,3078.0
F4=441*C/35.0; F2=(441*B+5*F4)/9.0
Fk={0:0.0,2:F2,4:F4}
nth,nph=60,120
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*(2*np.pi/nph)
def Y(l,m): return sph_harm(m,l,PH,TH)
ms=list(range(-2,3))
Yd={m:Y(2,m) for m in ms}
Vsp={}
ang1={(k,q,m1,m3):np.sum(W*np.conj(Yd[m1])*np.conj(Y(k,q))*Yd[m3]) for k in (0,2,4) for q in range(-k,k+1) for m1 in ms for m3 in ms}
ang2={(k,q,m2,m4):np.sum(W*np.conj(Yd[m2])*Y(k,q)*Yd[m4]) for k in (0,2,4) for q in range(-k,k+1) for m2 in ms for m4 in ms}
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
def h1(Dq):
    h=np.zeros((5,5),complex)
    for n,(v,e) in orbs.items(): h+=e*Dq*np.outer(v,np.conj(v))
    return h
dets=[sum(1<<i for i in c) for c in itertools.combinations(range(N),6)]
idx={d:i for i,d in enumerate(dets)}
def par(x): return (-1)**bin(x).count('1')
def cdag_c(p,q,st):
    if not (st>>q)&1: return None
    sg=par(st & ((1<<q)-1)); st2=st^(1<<q)
    if (st2>>p)&1: return None
    sg*=par(st2 & ((1<<p)-1))
    return sg, st2|(1<<p)
# precompute one-body and two-body operators as sparse lists
def build(Dq):
    H1=h1(Dq)
    D=len(dets); H=np.zeros((D,D))
    hso={}
    for i,(m,s) in enumerate(so):
        for j,(mp,sp) in enumerate(so):
            if s==sp and abs(H1[m+2,mp+2])>1e-14: hso[(i,j)]=H1[m+2,mp+2].real
    for col,st in enumerate(dets):
        for (p,q),val in hso.items():
            r=cdag_c(p,q,st)
            if r: H[idx[r[1]],col]+=r[0]*val
        for a,b,c,d in itertools.product(range(N),repeat=4):
            v=Vt[a,b,c,d]
            if v==0 or b==a: continue
            # c_a^+ c_b^+ c_d c_c  (apply c_c first, then d, then b^+, then a^+)
            if not (st>>c)&1: continue
            s1=par(st & ((1<<c)-1)); t=st^(1<<c)
            if not (t>>d)&1 or d==c: continue
            s2_=par(t & ((1<<d)-1)); t^=(1<<d)
            if (t>>b)&1: continue
            s3=par(t & ((1<<b)-1)); t|=(1<<b)
            if (t>>a)&1: continue
            s4=par(t & ((1<<a)-1)); t|=(1<<a)
            H[idx[t],col]+=0.5*v*s1*s2_*s3*s4
    return H
Hs={}
def get(Dq):
    H=build(Dq0) if False else None
