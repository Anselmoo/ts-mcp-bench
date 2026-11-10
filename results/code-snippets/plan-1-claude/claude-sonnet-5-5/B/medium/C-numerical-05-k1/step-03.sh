python3 -c "
import numpy as np
from scipy.optimize import least_squares
for v in (4,6,2*6**.5,np.sqrt(6)*2):
  def f(p):
    D,B=p
    w=np.linalg.eigvalsh([[-6*D,v*B],[v*B,15*B]]);g=w[0]
    return [2*D-g-15730,w[1]-g-24030,12*D-g-32750]
  r=least_squares(f,[1900,700]);print(v,r.x,f(r.x))
"