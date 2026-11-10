python3 - <<'E'
import numpy as np
from scipy.optimize import fsolve
def T(D,B):
    return np.linalg.eigvalsh(np.array([[-8*D-5*B,-6*B],[-6*B,2*D+4*B]]))
def T2(D,B): return -8*D+B*0+ (-2*B)  # t2^2 3T2 = -8Dq+... placeholder
# 3T2: t2^2 = -8Dq+B ; te = 2Dq+... use te 3T2 = 2Dq-5B... check
def f(x):
    D,B=x;e=T(D,B);return [ (2*D-5*B+ (0)) - e[0]-17500 ,e[1]-e[0]-25000]
print(T(1875,583.333))
E