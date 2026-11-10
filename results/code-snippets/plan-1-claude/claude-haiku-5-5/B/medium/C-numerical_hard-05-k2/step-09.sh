python3 -c "
import numpy as np, itertools
import d6
from d6 import *
d6.basis6=lambda: [sum(1<<i for i in c) for c in itertools.combinations(range(10),2)]
for B,C in [(1.0,0.0),(0.0,1.0)]:
    h,V=build(B,C,0.0)
    b,H,S2=ops(h,V)
    w,U=np.linalg.eigh(H+100*S2)
    s2=np.diag(U.T@S2@U); e=np.diag(U.T@H@U)
    for val in sorted(set(np.round(s2,3))):
        print(B,C,'S(S+1)=',val, np.round(sorted(set(np.round(e[np.abs(s2-val)<1e-3],3))),3))
"