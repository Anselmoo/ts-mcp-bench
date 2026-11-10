timeout 900 python3 -c "
exec(open('ligf_run.py').read())
import numpy as np
from scipy.optimize import least_squares
def levels(Dq,B):
    F=B/0.013323  # F2 such that free-ion 4P-4F = 15B
    H=Hmat(Dq,F,0.625*F)
    e=np.linalg.eigvalsh((H+H.conj().T)/2)
    return np.sort(e.real)
# check free ion
e=levels(0,1000); print('free ion (B=1000) 4P-4F:', e[7]-e[0], e[-1]-e[0])
obs=np.array([8620,18410,20250.])
def res(p):
    Dq,B=p
    e=levels(Dq,B)
    rel=e-e[0]
    # tentative: nu1=10Dq -> sorted levels; use 4T2g=, 4A2g, 4T1g(P) : pick the 3 lowest excited quartet-level energies
    ex=rel[1:]
    return ex
# print spectrum for a trial to see structure
e=levels(862,900)
print('rel levels Dq=862 B=900:', np.round(e-e[0],0))
"