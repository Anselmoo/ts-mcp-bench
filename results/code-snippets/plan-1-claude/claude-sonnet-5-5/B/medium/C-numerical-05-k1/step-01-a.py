import numpy as np
from scipy.optimize import least_squares
def f(p):
    D,B=p
    w=np.linalg.eigvalsh([[-6*D,4*B],[4*B,15*B]]);g=w[0]
    return [2*D-g-15730,w[1]-g-24030,12*D-g-32750]
r=least_squares(f,[1900,700]);print(r.x,f(r.x))
