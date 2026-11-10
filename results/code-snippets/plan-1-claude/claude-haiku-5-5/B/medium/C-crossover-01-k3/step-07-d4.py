
from scipy.optimize import brentq
def f(Dq):
    H=Hee+np.diag(Dq*Hcf)
    P=S2-2*3*np.eye(nd)
    return np.linalg.eigvalsh(H+1e6*P@P)[0] - (-6*Dq)  # triplet ground minus quintet ground (penalized)
# check min over triplet vs quintet directly
for Dq in [600,700,800,900]:
    print(Dq, lowest_by_spin(Dq))
Dqc=brentq(f,500,1000,xtol=1e-6)
print("Dq_c =",Dqc, "Dq/B=",Dqc/B, "C/B=",C/B)
