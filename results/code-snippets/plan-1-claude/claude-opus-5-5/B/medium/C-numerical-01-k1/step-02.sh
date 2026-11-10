python3 -c "
from scipy.optimize import least_squares
import numpy as np,itertools
def nu(p):
 D,B=p;R=np.sqrt(100*D*D-180*D*B+225*B*B)
 return np.array([5*D-7.5*B+R/2,R,15*D-7.5*B+R/2])
obs=np.array([20700,30570,42990])
for perm in itertools.permutations(range(3)):
 o=obs[list(perm)]
 for g in [(1000,500),(2000,700),(3000,300),(1500,1000)]:
  r=least_squares(lambda p:nu(p)-o,g,bounds=([0,0],[1e4,5e3]));print(perm,r.x.round(1),np.abs(r.fun).max().round(0))
"