import numpy as np
from scipy.optimize import least_squares
obs=np.array([20700,30570,42990])
def m(p,k=6):
    D,B=p
    w=np.linalg.eigvalsh([[-6*D,k*B],[k*B,15*B]]);g=w[0]
    return np.array([2*D-g,w[1]-g,12*D-g])
for k in(4,6):
    r=least_squares(lambda p:m(p,k)-obs,[2000,800]);print(k,r.x,m(r.x,k))
