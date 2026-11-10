python3 -c "
from scipy.optimize import fsolve,least_squares
import numpy as np
def nu(p):
 D,B=p;R=np.sqrt(100*D*D-180*D*B+225*B*B)
 return np.array([5*D-7.5*B+R/2,R,15*D-7.5*B+R/2])
obs=np.array([20700,30570,42990])
for idx in [(0,1),(0,2),(1,2)]:
 s=fsolve(lambda p:(nu(p)-obs)[list(idx)],[2000,600]);print(idx,s,nu(s))
r=least_squares(lambda p:nu(p)-obs,[2000,600]);print(r.x,nu(r.x))
"