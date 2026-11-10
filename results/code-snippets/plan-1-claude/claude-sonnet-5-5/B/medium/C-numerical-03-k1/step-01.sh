python3 -c "
import numpy as np
from scipy.optimize import least_squares
def f(p):
    D,B=p
    s=np.sqrt((7.5*B+6*D)**2+36*B*B);Em=7.5*B-s;Ep=7.5*B+s
    return [2*D-Em,Ep-Em,12*D-Em]
o=[15490,24500,32330]
for g in [(1700,800),(1500,700),(900,500)]:
    r=least_squares(lambda p:np.array(f(p))-o,g);print(r.x,f(r.x))
"