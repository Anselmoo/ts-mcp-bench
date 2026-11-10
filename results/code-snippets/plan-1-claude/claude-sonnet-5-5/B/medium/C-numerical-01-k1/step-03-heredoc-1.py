import numpy as np
from scipy.optimize import least_squares
def m(p,k):
    D,B=p
    w=np.linalg.eigvalsh([[-6*D,k*B],[k*B,15*B]]);g=w[0]
    return np.array([2*D-g,w[1]-g,12*D-g])
obs=np.array([20700,30570,42990])
for k in(4,6):
  for idx in([0,1],[0,2],[1,2]):
    r=least_squares(lambda p:(m(p,k)-obs)[idx],[2000,800]);print(k,idx,r.x,m(r.x,k),r.cost)
