cd /tmp && python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
l=2; ms=[-2,-1,0,1,2]
def G(k,ma,q,mc):
    if abs(q)>k or (-ma+q+mc)!=0: return 0.0
    return float(gaunt(l,k,l,-ma,q,mc))
def ang(k,a,b,c,d):
    if a+b!=c+d: return 0.0
    s=0.0
    for q in range(-k,k+1):
        s+=((-1)**(a+q))*G(k,a,-q,c)*((-1)**b)*G(k,b,q,d)
    return 4*np.pi/(2*k+1)*s
A={}
for k in (0,2,4):
    T=np.zeros((5,5,5,5))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        T[a,b,c,d]=ang(k,ms[a],ms[b],ms[c],ms[d])
    A[k]=T
print('sym err', np.abs(A[2]-A[2].transpose(2,3,0,1)).max(), np.abs(A[2]-A[2].transpose(1,0,3,2)).max())
print('F0 check diag', A[0][0,1,0,1], A[0][0,1,1,0])
print('F2 check', A[2][0,4,0,4], A[2][2,2,2,2])
EOF