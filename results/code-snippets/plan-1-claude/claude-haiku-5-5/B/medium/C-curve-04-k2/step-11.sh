python3 - << 'EOF'
import numpy as np
from math import pi, sqrt
from scipy.linalg import expm
lz=np.diag([-2.,-1,0,1,2]).astype(complex)
lp=np.zeros((5,5),dtype=complex)
for m in range(-2,2):
    lp[m+3,m+2]=sqrt(6-m*(m+1))
lm=lp.conj().T
lx=(lp+lm)/2; ly=(lp-lm)/(2j)
Lops=[lx,ly,lz]
print('commutator check', np.abs(lx@ly-ly@lx-1j*lz).max())
def Dmat(n,th): return expm(-1j*th*sum(n[i]*Lops[i] for i in range(3)))
D1=Dmat([0,0,1],pi/2); D2=Dmat([1,1,1],2*np.pi/3)
print('unitary', np.abs(D1@D1.conj().T-np.eye(5)).max())
print('C4^4=1', np.abs(np.linalg.matrix_power(D1,4)-np.eye(5)).max())
print('trace C4', np.trace(D1), 'trace C3', np.trace(D2))
EOF