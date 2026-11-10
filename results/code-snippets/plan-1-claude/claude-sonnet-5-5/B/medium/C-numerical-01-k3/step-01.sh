python3 -c "
import numpy as np
from scipy.optimize import least_squares
def f(p):
    D,B=p
    w,_=np.linalg.eigh(np.array([[-6*D,4*B],[4*B,15*B+6*D]]))
    g=w[0]
    return [2*D-g-20700,12*D-g-30570,w[1]-g-42990]
for o in [0]:
    r=least_squares(f,[2000,700]);print(r.x,r.fun)
def h(p):
    D,B=p
    w,_=np.linalg.eigh(np.array([[-6*D,4*B],[4*B,15*B+6*D]]))
    g=w[0]
    return [2*D-g-20700,w[1]-g-30570,12*D-g-42990]
r=least_squares(h,[2000,700]);print(r.x,r.fun)
"