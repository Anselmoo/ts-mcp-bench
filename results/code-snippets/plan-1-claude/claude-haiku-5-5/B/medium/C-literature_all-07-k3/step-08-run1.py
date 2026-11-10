import numpy as np
from many import *
def energies(Dq,B,C):
    Hm=spectrum(Dq,B,C)
    S=Hm[np.ix_(sec,sec)]
    e=np.linalg.eigvalsh(S)
    e6=np.linalg.eigvalsh(Hm[np.ix_(sec5,sec5)])[0]
    return e-e6, e6
for C in [0,1,4]:
    e,e6=energies(0.0,1.0,C)
    print("C=",C,"free-ion quartets (rel. sextet, units B):",np.round(e,4))
