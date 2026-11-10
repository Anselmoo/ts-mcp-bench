import numpy as np
from scipy.optimize import least_squares
obs=np.array([15490,24500,32330])
def f(p):
    D,B=p;S=np.sqrt((7.5*B+6*D)**2+36*B*B);Em=7.5*B-S
    return np.sort([2*D-Em,12*D-Em,2*S])-obs
for g in [(1700,700),(900,600),(2000,800)]:
    r=least_squares(f,g);print(r.x,r.fun)
