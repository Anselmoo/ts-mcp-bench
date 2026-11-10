python3 -c "
import numpy as np
from scipy.optimize import least_squares
def f(p):
    D,B=p
    w=np.linalg.eigvalsh([[-6*D,4*B],[4*B,15*B]])
    return [2*D-w[0]-8620,12*D-w[0]-18410,w[1]-w[0]-20250]
for g in [(1000,900),(1200,800)]:
    r=least_squares(f,g);print(r.x,r.fun)
"