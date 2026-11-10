
mkdir -p ~/d7 && cd ~/d7 && cat << 'EOF' > d7.py
import numpy as np, itertools
from scipy.optimize import least_squares
from scipy.special import sph_harm
ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0,1)]
N=10
xg,wg=np.polynomial.legendre.leggauss(20)
phi=np.linspace(0,2*np.pi,48,endpoint=False)
TT,PP=np.meshgrid(np.arccos(xg),phi,indexing='ij')
W=np.outer(wg,np.ones(len(phi)))*(2*np.pi/len(phi))
def Y(l,m): return sph_harm(m,l,PP,TT)
# A[k][m1,m3,q] = int Y_{2m1}^* Y_{kq} Y_{2m3}
A={}
for k in (0,2,4):
    for m1 in ms:
        for m3 in ms:
            for q in range(-k,k+1):
                A[(k,m1,m3,q)]=np.sum(W*np.conj(Y(2,m1))*Y(k,q)*Y(2,m3))
def ang(k,m1,m3,m2,m4):
    s=0
    for q in range(-k,k+1):
        s+=A[(k,m1,m3,q)]*np.conj(A[(k,m2,m4,q)])   # int Y_m2^* Y_kq^* Y_m4 = conj(int Y_m4^* Y_kq Y_m2)... check below
    return 4*np.pi/(2*k+1)*s
def build(Dq,F0,F2,F4):
    G={0:F0,2:F2,4:F4}
    e1=np.zeros(5,complex); e1[2]=1
    e2=np.zeros(5,complex); e2[0]=1/np.sqrt(2); e2[4]=1/np.sqrt(2)
    P=np.outer(e1,e1.conj())+np.outer(e2,e2.conj())
    Vm=-4*Dq*np.eye(5)+10*Dq*P
    h=np.zeros((N,N),complex)
    for i,(m1,s1) in enumerate(so):
        for j,(m2,s2) in enumerate(so):
            if s1==s2: h[i,j]=Vm[m1+2,m2+2]
    g=np.zeros((N,N,N,N),complex)
    for i,(m1,s1) in enumerate(so):
      for j,(m2,s2) in enumerate(so):
        for k_,(m3,s3) in enumerate(so):
          for l,(m4,s4) in enumerate(so):
            if s1!=s3 or s2!=s4: continue
            g[i,j,k_,l]=sum(G[k]*ang(k,m1,m3,m2,m4) for k in (0,2,4))
    return h,g
EOF
python3 -c "
import sys; sys.path.insert(0,'.')
from d7 import *
# check: sum over Coulomb: F0 term diagonal should be 1 for same orbital pair with k=0
print(ang(0,0,0,0,0), ang(0,2,2,-1,-1))
"