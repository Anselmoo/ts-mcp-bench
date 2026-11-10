python3 -c "
import numpy as np
from scipy.optimize import least_squares
def f(p):
    D,B=p
    w=np.linalg.eigvalsh([[-6*D,6*B],[6*B,15*B+6*D]])
    g=w[0]
    return [2*D-g-8620,12*D-g-18410,w[1]-g-20250]
r=least_squares(f,[1000,800]);print(r.x,r.fun)
"