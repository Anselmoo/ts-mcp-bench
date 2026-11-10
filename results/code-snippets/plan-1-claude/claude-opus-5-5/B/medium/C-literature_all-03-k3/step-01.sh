python3 -c "
import numpy as np;from scipy.optimize import least_squares as L
o=np.array([12300,18500,27900])
def f(p):
 D,B=p;s=np.sqrt(225*B*B+100*D*D-180*B*D);return np.array([10*D,15*D+7.5*B-s/2,15*D+7.5*B+s/2])-o
r=L(f,[1200,600]);print(r.x,f(r.x))
for D in [1230]:
 from scipy.optimize import brentq
 print(brentq(lambda B:f([D,B])[1],100,2000),brentq(lambda B:f([D,B])[2],100,2000))"