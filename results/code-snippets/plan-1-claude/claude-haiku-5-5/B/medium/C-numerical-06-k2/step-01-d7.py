import numpy as np
from scipy.optimize import least_squares
# d7 high-spin quartet model (4F/4P, T1g block, Racah off-diagonal 6*sqrt(3)*B)
def bands(p):
    Dq,B=p
    H=np.array([[-8*Dq, 6*np.sqrt(3)*B],[6*np.sqrt(3)*B, 15*B]])
    Em,Ep=np.linalg.eigvalsh(H)
    nu1=2*Dq-Em      # 4T2g
    nu2=18*Dq-Em     # 4A2g
    nu3=Ep-Em        # 4T1g(P)
    return np.array([nu1,nu2,nu3])
obs=np.array([9180,19550,20320.])
r=least_squares(lambda p: bands(p)-obs,[900,800])
print(r.x, bands(r.x), r.fun)
