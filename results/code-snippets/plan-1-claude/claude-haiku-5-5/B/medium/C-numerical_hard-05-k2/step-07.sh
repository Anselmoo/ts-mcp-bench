python3 -c "
import numpy as np
from d6 import *
h,V=build(1.0,4.5,0.0)
b,H,S2=ops(h,V)
w,U=np.linalg.eigh(H+100*S2)
s2=np.diag(U.T@S2@U)
for S in [0,2,6]:
    pass
import collections
ev=np.linalg.eigvalsh(H)
trip=np.linalg.eigvalsh(H+100*S2)
for target in [0,2,6]:
    pass
# quintet lowest
vals=[]
for Sv in [0,2,6]:
    sub=np.linalg.eigvalsh(H+100*(S2-Sv*(Sv+2)/4*0 ))
print(np.round(np.sort(np.diag(U.T@H@U))[:3],3))
# S=2 (S(S+1)=6) energies
e=np.diag(U.T@H@U)
print('S2 values', sorted(set(np.round(s2,3))))
for val in sorted(set(np.round(s2,3))):
    print(val, np.round(sorted(e[np.abs(s2-val)<1e-3])[:3],3))
"