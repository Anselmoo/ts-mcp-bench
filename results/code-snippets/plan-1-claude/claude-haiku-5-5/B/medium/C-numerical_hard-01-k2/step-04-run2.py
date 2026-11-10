import numpy as np, fit as Fm, d4lib as L
from scipy.optimize import least_squares
S2=Fm.S2
ws,vs=np.linalg.eigh(S2)
def block(S):
    P=vs[:, np.abs(ws-S*(S+1))<1e-6]
    return P
Ptrip=block(1); Pq=block(2); Psing=block(0)
print(Ptrip.shape,Pq.shape,Psing.shape)
def levels(Dq,B):
    H=L.oneel(L.cf_matrix(Dq))
    C=4.7*B; F4=441*C/35; F2=(441*B+5*F4)/9
    H=H+F2*Fm.E2+F4*Fm.E4
    H=(H+H.conj().T)/2
    Ht=Ptrip.conj().T@H@Ptrip
    w=np.linalg.eigvalsh(Ht)
    return np.sort(w.real)
# ground for B=800, Dq=2000
w=levels(2000,800)
print(np.round(w-w[0],1))
