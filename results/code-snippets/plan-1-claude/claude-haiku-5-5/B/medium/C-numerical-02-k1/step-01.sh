
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from scipy.optimize import least_squares
from scipy.special import sph_harm
# spin-orbitals: index = 2*(m+2)+s, s=0 up,1 down
ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0,1)]
N=10
# angular integrals (complex Y, quadrature)
xg,wg=np.polynomial.legendre.leggauss(30)
phi=np.linspace(0,2*np.pi,64,endpoint=False)
TH=np.arccos(xg)
TT,PP=np.meshgrid(TH,phi,indexing='ij')
W=np.outer(wg,np.ones(len(phi)))*(2*np.pi/len(phi))
def Y(l,m): return sph_harm(m,l,PP,TT)
def gaunt(m1,k,q,m3):
    # int Y_{2m1}^* Y_{kq}^* Y_{2m3}
    return np.sum(W*np.conj(Y(2,m1))*np.conj(Y(k,q))*Y(2,m3))
# two-electron: <m1 m2|g|m3 m4> = sum_k F^k * ang_k
def ang(k,m1,m2,m3,m4):
    tot=0
    for q in range(-k,k+1):
        tot+=4*np.pi/(2*k+1)*gaunt(m1,k,q,m3)*np.conj(gaunt(m2,k,q,m4))*0
    # correct: int Y_{m1}^*(1)Y_{m3}(1) Y_kq(1)^* ... use full expression below
    return tot
# build angular coefficient a_k(m1,m3;m2,m4) = sum_q (4pi/(2k+1)) <m1|C^k_q^*|m3><m2|C^k_{-q}|m4>, use direct integrals
def ang_coef(k,m1,m3,m2,m4):
    s=0
    for q in range(-k,k+1):
        A=np.sum(W*np.conj(Y(2,m1))*Y(k,q)*Y(2,m3))   # int Y_m1^* Y_kq Y_m3
        B=np.sum(W*np.conj(Y(2,m2))*np.conj(Y(k,q))*Y(2,m4))
        s+=A*B
    return 4*np.pi/(2*k+1)*s
def build(Dq,F0,F2,F4,spin_idx=None):
    # Slater-Condon coefficient table
    G={}
    for k,F in ((0,F0),(2,F2),(4,F4)):
        G[k]=F
    V=np.zeros((N,N),complex)
    # one-electron: -4Dq + 10Dq P_eg in complex basis
    eg=np.zeros(5,complex); eg[2]=1; eg[0]=1/np.sqrt(2); eg[4]=1/np.sqrt(2)
    # eg = {|0>, (|2>+|-2>)/sqrt2}
    e1=np.zeros(5,complex); e1[2]=1
    e2=np.zeros(5,complex); e2[0]=1/np.sqrt(2); e2[4]=1/np.sqrt(2)
    P=np.outer(e1,e1.conj())+np.outer(e2,e2.conj())
    Vm=-4*Dq*np.eye(5)+10*Dq*P
    h=np.zeros((N,N),complex)
    for i,(m1,s1) in enumerate(so):
        for j,(m2,s2) in enumerate(so):
            if s1==s2: h[i,j]=Vm[m1+2,m2+2]
    # two-electron integrals <ij|g|kl>
    g=np.zeros((N,N,N,N),complex)
    for i,(m1,s1) in enumerate(so):
      for j,(m2,s2) in enumerate(so):
        for k_,(m3,s3) in enumerate(so):
          for l,(m4,s4) in enumerate(so):
            if s1!=s3 or s2!=s4: continue
            val=0
            for k in (0,2,4):
                val+=G[k]*ang_coef(k,m1,m3,m2,m4)
            g[i,j,k_,l]=val
    return h,g
EOF
echo ok