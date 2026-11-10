python3 -c "
import numpy as np
from scipy.optimize import least_squares
def m(p):
  D,B=p; s=7.5*B+15*D; r=0.5*np.sqrt(225*B*B-180*B*D+400*D*D)
  return np.array([10*D,s-r,s+r])
obs=np.array([4330,7520,18640])
for g in [(433,800),(500,700),(700,900)]:
  r=least_squares(lambda p:m(p)-obs,g); print(r.x,m(r.x))
D=433
for B in np.arange(500,1200,50): print(B,m((D,B)))
"