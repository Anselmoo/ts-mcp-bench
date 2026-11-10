python3 -c "
import numpy as np;from scipy.optimize import least_squares as L
def f(p):
 D,B=p;s=np.sqrt(225*B*B-180*B*D+100*D*D)/2
 return [10*D-10600,15*D+7.5*B-s-17500,15*D+7.5*B+s-27600]
r=L(f,[1000,900]);print(r.x,f(r.x))"