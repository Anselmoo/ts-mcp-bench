python3 - <<'E'
import numpy as np
from scipy.optimize import least_squares
def m(p):
    D,B=p
    w=np.linalg.eigvalsh([[-6*D,4*D],[4*D,15*B]]);g=w[0]
    return np.array([2*D-g,w[1]-g,12*D-g])
obs=np.array([20700,30570,42990])
r=least_squares(lambda p:m(p)-obs,[2200,800]);print(r.x,m(r.x))
E