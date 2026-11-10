python3 -c "
import numpy as np
from scipy.optimize import least_squares
def m(p):
 D,B=p
 s=np.sqrt(225*B*B-180*B*D+100*D*D)
 return np.array([10*D,7.5*B+15*D-s/2,7.5*B+15*D+s/2])
o=np.array([12300,18500,27900])
r=least_squares(lambda p:m(p)-o,[1230,650]);print(r.x,m(r.x))"