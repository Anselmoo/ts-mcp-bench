import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
l=2
ms=list(range(-l,l+1))
def red(k): return float((-1)**l*(2*l+1)*wigner_3j(l,k,l,0,0,0))
def Cmat(k,q):
    M=np.zeros((5,5))
    for i,m in enumerate(ms):
        for j,mp in enumerate(ms):
            if -m+q+mp!=0 or abs(q)>k: continue
            M[i,j]=float((-1)**(l-m)*wigner_3j(l,k,l,-m,q,mp))*red(k)
    return M
Mc=Cmat(4,0)+np.sqrt(5/14)*(Cmat(4,4)+Cmat(4,-4))
Mc2=Cmat(4,0)-np.sqrt(5/14)*(Cmat(4,4)+Cmat(4,-4))
for M in (Mc,Mc2):
    print(np.round(np.linalg.eigvalsh(M),4))
