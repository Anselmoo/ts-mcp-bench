import numpy as np
from ff import build_V
from fock import hamiltonian
from ff import build_h
import sys
h0=np.zeros((10,10))
for F2,F4 in [(1.0,0.625),(0.5,0.3),(1.0,0.5)]:
    F={0:0.0,2:F2,4:F4}
    V=build_V(F)
    H,b=hamiltonian(2,h0,V)
    ev=np.linalg.eigvalsh(H)
    print(F2,F4,np.round(np.unique(np.round(ev,6)),6))
