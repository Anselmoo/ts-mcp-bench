python3 -c "
import numpy as np
from scipy.optimize import least_squares
def f(p):
    D,B=p
    M=np.array([[-6*D,6*B],[6*B,15*B+6*D]]);e=np.linalg.eigvalsh(M)
    return [2*D-e[0]-8620,12*D-e[0]-18410,e[1]-e[0]-20250]
for g in([900,800],[1000,900]):
    r=least_squares(f,g);print(r.x,r.fun)
"