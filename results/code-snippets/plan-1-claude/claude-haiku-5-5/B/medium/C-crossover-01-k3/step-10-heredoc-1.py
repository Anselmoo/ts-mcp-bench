import numpy as np
exec(open('d4.py').read().split("for Dq in [0,500")[0])
from scipy.optimize import brentq
def lo(Dq,S):
    H=Hee+np.diag(Dq*Hcf); P=S2-S*(S+1)*np.eye(nd)
    return np.linalg.eigvalsh(H+1e6*P@P)[0]
f=lambda D: lo(D,1)+6*D
D1=brentq(f,1000,2000,xtol=1e-6)
print("triplet crossing Dq=",D1, "Dq/B=",D1/B)
g=lambda D: lo(D,0)+6*D
print("singlet crossing: ", brentq(g,500,1500,xtol=1e-6))
