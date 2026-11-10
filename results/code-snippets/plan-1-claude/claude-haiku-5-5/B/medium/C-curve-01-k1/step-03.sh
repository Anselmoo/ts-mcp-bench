mkdir -p /tmp/w && cd /tmp/w && cat > d4.py <<'EOF'
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
def Y(l,m): return sph_harm(m,l,PP,TT)
ms=list(range(-2,3))
orbs=[(m,s) for m in ms for s in (0,1)]
N=len(orbs)
Ycache={(l,m):Y(l,m) for l in (2,4) for m in range(-l,l+1)}
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
# Fock space, Jordan-Wigner-like sign
dim=2**N
nel=np.array([bin(s).count('1') for s in range(dim)])
idx=np.where(nel==4)[0]
pos={s:i for i,s in enumerate(idx)}
def E_op(i,j):
    """one-body c^+_i c_j restricted to 4-electron sector"""
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
E={}
for i in range(N):
    for j in range(N):
        E[(i,j)]=E_op(i,j)
D=len(idx)
Hee=csr_matrix((D,D),dtype=complex)
for a in range(N):
 for b in range(N):
  for c in range(N):
   for d in range(N):
    v=g[a,b,c,d]
    if abs(v)<1e-12: continue
    term=E[(a,c)]@E[(b,d)]
    if b==c: term=term-E[(a,d)]
    Hee=Hee+0.5*v*term
Hee=Hee.toarray()
# Single-particle orbital basis: complex m basis. Build cubic field matrix h (per spin)
# real d orbitals in complex basis: index by m
def vec(d):
    v=np.zeros(5,dtype=complex)
    for m,c in d.items(): v[m+2]=c
    return v
s2=1/np.sqrt(2)
t2g=[vec({1:-s2,-1:s2}), vec({2:s2/1j*1 ,-2:-s2/1j}) , vec({1:1j*s2,-1:1j*s2})]
eg=[vec({0:1}), vec({2:s2,-2:s2})]
# normalize t2g: dxz ~ (|1>-|-1>), dyz ~ i(|1>+|-1>), dxy ~ (|2>-|-2>)/i
t2g=[vec({1:-s2,-1:s2}), vec({2:-1j*s2,-2:1j*s2}), vec({1:1j*s2,-1:1j*s2})]
for v in t2g+eg: assert abs(np.vdot(v,v)-1)<1e-12
def proj(vs): return sum(np.outer(v,np.conj(v)) for v in vs)
h1=-4*proj(t2g)+6*proj(eg)   # times Dq
# orbital index ordering: orbs with (m,s): index 2*(m+2)+s
def h_spin(hm):
    H=np.zeros((N,N),dtype=complex)
    for a,(m1,s1) in enumerate(orbs):
        for b,(m2,s2_) in enumerate(orbs):
            if s1==s2_: H[a,b]=hm[m1+2,m2+2]
    return H
H1=h_spin(h1)
# one-body operator in Fock: sum H1[a,b] c+_a c_b
Hcf_base=np.zeros((D,D),dtype=complex)
for a in range(N):
    for b in range(N):
        if abs(H1[a,b])>1e-12: Hcf_base+=H1[a,b]*E[(a,b)].toarray()
# rotation generators L_z, L_x, L_y, l=2 in m basis
def Lmats(l=2):
    ms_=np.arange(-l,l+1)
    Lz=np.diag(ms_).astype(complex)
    Lp=np.zeros((2*l+1,2*l+1),dtype=complex)
    for i,m in enumerate(ms_[:-1]):
        Lp[i+1,i]=np.sqrt(l*(l+1)-m*(m+1))
    Lx=(Lp+Lp.conj().T)/2; Ly=(Lp-Lp.conj().T)/(2j)
    return Lx,Ly,Lz
Lx,Ly,Lz=Lmats()
def rot_op(axis,angle):
    n=np.array(axis,float); n=n/np.linalg.norm(n)
    Ln=n[0]*Lx+n[1]*Ly+n[2]*Lz
    u=expm(-1j*angle*Ln)  # 5x5 single particle
    Us=h_spin(u)
    # many-body: Gamma(u)=exp(sum log(u)_ab c+_a c_b)  -> use exp of generator
    G=expm(-1j*angle*(n[0]*Lx+n[1]*Ly+n[2]*Lz))
    # generator operator
    Gop=np.zeros((D,D),dtype=complex)
    Hs=h_spin(n[0]*Lx+n[1]*Ly+n[2]*Lz)
    for a in range(N):
        for b in range(N):
            if abs(Hs[a,b])>1e-12: Gop+=Hs[a,b]*E[(a,b)].toarray()
    return expm(-1j*angle*Gop)
EOF
python3 -c "
import sys; sys.path.insert(0,'/tmp/w')
import d4; print('F2,F4',d4.F2,d4.F4); print(d4.Hee.shape); import numpy as np; print(np.allclose(d4.Hee,d4.Hee.conj().T))"