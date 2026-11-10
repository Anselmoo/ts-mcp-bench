python3 -c "
import numpy as np
from scipy.optimize import least_squares,fsolve
def f(p):
    D,B=p;m=7.5*B;s=np.sqrt((7.5*B+6*D)**2+36*B**2);Em=m-s;Ep=m+s
    return np.array([2*D-Em,Ep-Em,12*D-Em])
o=np.array([15730,24030,32750])
r=least_squares(lambda p:f(p)-o,[1700,800]);print(r.x,f(r.x))
for pair in [(0,1),(0,2),(1,2)]:
    s=least_squares(lambda p:(f(p)-o)[list(pair)],[1700,800]);print(pair,s.x,f(s.x))
"