python3 -c "
import numpy as np
from scipy.optimize import least_squares
def f(p):
 D,B=p;a=7.5*B+15*D;s=0.5*np.sqrt(225*B*B-180*B*D+100*D*D)
 return [10*D-10600,a-s-17500,a+s-27600]
r=least_squares(f,[1000,900]);print(r.x,f(r.x))
for B in [886.7]:print(f([1060,B]))
"