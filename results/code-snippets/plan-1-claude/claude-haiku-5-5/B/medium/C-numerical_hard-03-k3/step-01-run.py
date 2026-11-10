import sys; sys.path.insert(0,'/tmp')
from d5 import *
# S^2 operator for spin: build via Sz and S+ S- ; simpler: compute S^2 eigen via Sz-sectors
Hs = None
import numpy as np
B=1.0; C=4.6
def spectrum(x):
    H=build(x*B,B,C*B)
    # S^2 operator
    # total spin: Sz sector is 0 for these states (5 electrons, Sz=±1/2 etc.) ; use Sz=1/2 subspace (3 up 2 down... ) 
    w,v=np.linalg.eigh(H)
    return w
# Spin projection: build S^2 numerically
def S2op():
    n=len(states); S2=np.zeros((n,n))
    # S^2 = S- S+ + Sz(Sz+1)
    Sp=np.zeros((n,n)); 
    for si,s in enumerate(states):
        for o in range(5):
            # c+_{o,up} c_{o,down}
            r=cdag_c(2*o,2*o+1,s)
            if r: Sp[idx[r[1]],si]+=r[0]
    Sz=np.zeros(n)
    for si,s in enumerate(states):
        Sz[si]=0.5*sum(((s>>(2*o))&1)-((s>>(2*o+1))&1) for o in range(5))
    S2=Sp.T@Sp+np.diag(Sz*(Sz+1))  # S+^dag S+ = S- S+ ; but Sp is S+ (up-raising? c+up c down raises Sz)
    return S2
S2=S2op()
np.save('/tmp/S2.npy',S2)
