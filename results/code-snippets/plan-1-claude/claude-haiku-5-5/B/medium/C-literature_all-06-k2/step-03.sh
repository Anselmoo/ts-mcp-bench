mkdir -p /tmp/w && cat > /tmp/w/d3.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import fsolve
xg,wg=np.polynomial.legendre.leggauss(30)
phis=np.linspace(0,2*np.pi,60,endpoint=False); wp=2*np.pi/60
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij'); W=np.outer(wg,np.ones(len(phis)))*wp
ms=list(range(-2,3))
def Y(k,q,th=TH,ph=PH): return sph_harm_y(k,q,th,ph)
Yc={m:Y(2,m) for m in ms}
Vc={k:np.zeros((5,5,5,5),complex) for k in (0,2,4)}
for k in (0,2,4):
  Ykq={q:Y(k,q) for q in range(-k,k+1)}
  for ia,a in enumerate(ms):
    for ic,c in enumerate(ms):
      G1={q:np.sum(W*np.conj(Yc[a])*Yc[c]*np.conj(Ykq[q])) for q in range(-k,k+1)}
      for ib,b in enumerate(ms):
        for id_,d in enumerate(ms):
          s=0
          for q in range(-k,k+1):
            s+=G1[q]*np.sum(W*np.conj(Yc[b])*Yc[d]*Ykq[q])
          Vc[k][ia,ib,ic,id_]=4*np.pi/(2*k+1)*s
# real orbitals: rows = xy,yz,xz,z2,x2y2 ; cols m=-2..2
s2=np.sqrt(2); I=1j
U=np.zeros((5,5),complex)
U[0,0]=1/(I*s2); U[0,4]=-1/(I*s2)      # xy
U[1,1]=1/(I*s2); U[1,3]=1/(I*s2)       # yz
U[2,1]=-1/s2;    U[2,3]=1/s2           # xz
U[3,2]=1                               # z2
U[4,0]=1/s2;     U[4,4]=1/s2           # x2-y2
# check orthonormal
assert np.allclose(U@U.conj().T,np.eye(5)), np.round(U@U.conj().T,3)
Vr={}
for k in Vc:
  Vr[k]=np.einsum('ai,bj,ck,dl,ijkl->abcd',U.conj(),U.conj(),U,U,Vc[k])
# Fock space, 10 spin-orbitals: index 2*orb+spin
N=10
def cop(i):
    # annihilation operator Jordan-Wigner on 2^N
    dim=2**N; M=np.zeros((dim,dim))
    for s in range(dim):
        if (s>>i)&1:
            sign=(-1)**bin(s & ((1<<i)-1)).count('1')
            M[s^(1<<i),s]=sign
    return M
import scipy.sparse as sp
c=[sp.csr_matrix(cop(i)) for i in range(N)]
cd=[x.T.tocsr() for x in c]
# basis of N=3 states
states=[s for s in range(2**N) if bin(s).count('1')==3]
idx={s:i for i,s in enumerate(states)}
def restrict(M):
    M=M.tocsr()[states][:,states]
    return M.toarray()
# one-body LF: orbitals orb index: xy0,yz1,xz2,z2 3,x2y2 4 ; spin
def build_H(Dq,B,C):
    F4=C*63/5.0          # from C=35F4/441 -> F4=441C/35 ; use 441/35
    F4=441*C/35.0
    F2=(441*B+5*F4)/9.0
    Fk={0:0.0,2:F2,4:F4}
    H=sp.csr_matrix((len(states),len(states)))
    eps=[-4*Dq,-4*Dq,-4*Dq,6*Dq,6*Dq]
    for o in range(5):
        for sp_ in range(2):
            i=2*o+sp_
            H=H+eps[o]*restrict(cd[i]@c[i])
    # two-body: 1/2 sum V_{abcd} c+_a c+_b c_d c_c, spin-conserving
    for k in (2,4):
        V=Fk[k]*Vr[k]
        for o1,o2,o3,o4 in itertools.product(range(5),repeat=4):
            v=V[o1,o2,o3,o4]
            if abs(v)<1e-12: continue
            for s1 in range(2):
              for s2_ in range(2):
                a=2*o1+s1; b=2*o2+s2_; cc=2*o3+s1; dd=2*o4+s2_
                # term: c+_a c+_b c_d c_c, spin: a,c same spin; b,d same spin
                H=H+0.5*v*restrict(cd[a]@cd[b]@c[dd]@c[cc])
    return H.toarray()
def spectrum(Dq,B,C):
    H=build_H(Dq,B,C)
    return H
if __name__=="__main__":
    H=build_H(0,1.0,0.0)
    print(np.round(np.linalg.eigvalsh(H)[:5],6))
EOF
cd /tmp/w && time python3 d3.py