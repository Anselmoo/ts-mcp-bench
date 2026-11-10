import numpy as np
from scipy.special import sph_harm
from scipy.linalg import expm, eigh
from scipy.sparse import csr_matrix
B=821.0; C=3657.0
F4=63*C/5; F2=(441*B+5*F4)/9
Fk={2:F2,4:F4}
xg,wg=np.polynomial.legendre.leggauss(16)
nphi=32
phi=np.arange(nphi)*2*np.pi/nphi; wphi=2*np.pi/nphi
TH=np.arccos(xg)
TT,PP=np.meshgrid(TH,phi,indexing='ij'); W=np.outer(wg,np.ones(nphi))*wphi
ms=list(range(-2,3))
orbs=[(m,s) for m in ms for s in (0,1)]
N=len(orbs)
Ycache={(l,m):sph_harm(m,l,PP,TT) for l in (2,4) for m in range(-l,l+1)}
def ang(k,m1,m3,m2,m4):
    tot=0
    for q in range(-k,k+1):
        G1=np.sum(W*np.conj(Ycache[(2,m1)])*np.conj(Ycache[(k,q)])*Ycache[(2,m3)])
        G2=np.sum(W*np.conj(Ycache[(2,m2)])*Ycache[(k,q)]*Ycache[(2,m4)])
        tot+=G1*G2
    return 4*np.pi/(2*k+1)*tot
g=np.zeros((N,N,N,N),dtype=complex)
for a,(m1,s1) in enumerate(orbs):
  for b,(m2,s2) in enumerate(orbs):
    for c,(m3,s3) in enumerate(orbs):
      for d,(m4,s4) in enumerate(orbs):
        if s1!=s3 or s2!=s4: continue
        g[a,b,c,d]=sum(Fk[k]*ang(k,m1,m3,m2,m4) for k in (2,4))
dim=2**N
nel=np.array([bin(s).count('1') for s in range(dim)])
idx=np.where(nel==4)[0]
pos={s:i for i,s in enumerate(idx)}
def E_op(i,j):
    rows=[];cols=[];vals=[]
    for st in idx:
        if not (st>>j)&1: continue
        s1=st^(1<<j)
        sign=(-1)**bin(s1&((1<<j)-1)).count('1')
        if (s1>>i)&1: continue
        s2=s1|(1<<i)
        sign*=(-1)**bin(s2&((1<<i)-1)).count('1')
        rows.append(pos[s2]);cols.append(pos[st]);vals.append(sign)
    return csr_matrix((vals,(rows,cols)),shape=(len(idx),len(idx)))
E={(i,j):E_op(i,j) for i in range(N) for j in range(N)}
D=len(idx)
Hee=np.zeros((D,D),dtype=complex)
for a in range(N):
 for b in range(N):
  for c in range(N):
   for d in range(N):
    v=g[a,b,c,d]
    if abs(v)<1e-12: continue
    term=(E[(a,c)]@E[(b,d)]).toarray()
    if b==c: term=term-E[(a,d)].toarray()
    Hee+=0.5*v*term
def vec(dct):
    v=np.zeros(5,dtype=complex)
    for m,c in dct.items(): v[m+2]=c
    return v
s2=1/np.sqrt(2)
t2g=[vec({1:-s2,-1:s2}), vec({2:-1j*s2,-2:1j*s2}), vec({1:1j*s2,-1:1j*s2})]
eg=[vec({0:1}), vec({2:s2,-2:s2})]
def proj(vs): return sum(np.outer(v,np.conj(v)) for v in vs)
h1=-4*proj(t2g)+6*proj(eg)   # in units of Dq
def h_spin(hm):
    H=np.zeros((N,N),dtype=complex)
    for a,(m1,s1) in enumerate(orbs):
        for b,(m2,s2_) in enumerate(orbs):
            if s1==s2_: H[a,b]=hm[m1+2,m2+2]
    return H
def one_body(H1):
    Op=np.zeros((D,D),dtype=complex)
    for a in range(N):
        for b in range(N):
            if abs(H1[a,b])>1e-12: Op+=H1[a,b]*E[(a,b)].toarray()
    return Op
Hcf=one_body(h_spin(h1))
# spin operators
Sp=one_body(sum(h_spin(np.zeros((5,5)))[0:0] for _ in [0]) if False else np.zeros((N,N)))
Spl=np.zeros((D,D),dtype=complex); Sz=np.zeros((D,D),dtype=complex)
for mi,m in enumerate(ms):
    Spl+=E[(2*mi,2*mi+1)].toarray()   # c+_up c_down
    Sz+=0.5*(E[(2*mi,2*mi)].toarray()-E[(2*mi+1,2*mi+1)].toarray())
S2=Spl.conj().T@Spl+Sz@Sz+Sz   # S-S+ = S^2 - Sz^2 - Sz  => S^2 = S-S+ + Sz^2 + Sz ; here Spl=S+ , S-=S+^dag
S2=Spl.conj().T@Spl+Sz@Sz+Sz
Lx=np.zeros((5,5),complex); Lp=np.zeros((5,5),complex)
for i,m in enumerate(ms[:-1]): Lp[i+1,i]=np.sqrt(6-m*(m+1))
Lx=(Lp+Lp.conj().T)/2; Ly=(Lp-Lp.conj().T)/(2j); Lz=np.diag(np.array(ms,float)).astype(complex)
def rot(axis,angle):
    n=np.array(axis,float); n/=np.linalg.norm(n)
    Hs=h_spin(n[0]*Lx+n[1]*Ly+n[2]*Lz)
    return expm(-1j*angle*one_body(Hs))
