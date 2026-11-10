python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.special import sph_harm_y
ms=list(range(-2,3))
def a(k,m1,m2,m3,m4):
    s=0.0
    for q in range(-k,k+1):
        s+= float(gaunt(2,k,2,-m1,-q,m3)*gaunt(2,k,2,-m2,q,m4))*(-1)**(m1+q+m2)
    return 4*np.pi/(2*k+1)*s
print("a0 check", a(0,2,-1,2,-1), a(0,2,-1,-1,2), a(0,2,2,2,2))
A={}
for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
    A[(m1,m2,m3,m4)]=[a(k,m1,m2,m3,m4) for k in (0,2,4)]
th,wt=np.polynomial.legendre.leggauss(40)
phis=np.linspace(0,2*np.pi,80,endpoint=False)
Lvecs=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
T,P=np.meshgrid(np.arccos(th),phis,indexing='ij')
W=np.outer(wt,np.ones(len(phis)))*(2*np.pi/len(phis))
x=np.sin(T)*np.cos(P); y=np.sin(T)*np.sin(P); z=np.cos(T)
V=np.zeros_like(T)
for L in Lvecs:
    c=x*L[0]+y*L[1]+z*L[2]
    V+= 35*c**4/8-30*c**2/8+3/8
M=np.zeros((5,5),complex)
for i,m1 in enumerate(ms):
    for j,m2 in enumerate(ms):
        Y1=sph_harm_y(2,m1,T,P); Y2=sph_harm_y(2,m2,T,P)
        M[i,j]=np.sum(np.conj(Y1)*V*Y2*W)
print(np.round(np.linalg.eigvalsh(M),6))
print(np.round(M.real,4))
import sys
np.save('/dev/null',0) if False else None
globals()['A_']=A; globals()['M_']=M
EOF