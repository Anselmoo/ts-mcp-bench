python3 -c "
import numpy as np
from scipy.optimize import least_squares
def f(p):
    D,B=p
    M=np.array([[18*D,6*B],[6*B,15*B+12*D]]);e=np.linalg.eigvalsh(M)
    return [10*D-10600,e[0]-17500,e[1]-27600]
r=least_squares(f,[1060,800]);print(r.x,r.fun)
r=least_squares(lambda p:f(p)[1:],[1060,800]);print(r.x,r.fun)"