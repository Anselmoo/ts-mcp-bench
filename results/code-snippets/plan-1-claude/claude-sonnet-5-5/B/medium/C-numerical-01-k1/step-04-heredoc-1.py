import numpy as np
from scipy.optimize import least_squares
def m(p):
    D,B,k=p
    w=np.linalg.eigvalsh([[-6*D,k*B],[k*B,15*B]]);g=w[0]
    return np.array([2*D-g,w[1]-g,12*D-g])
obs=np.array([20700,30570,42990])
r=least_squares(lambda p:m(p)-obs,[2200,900,5]);print(r.x,m(r.x))
