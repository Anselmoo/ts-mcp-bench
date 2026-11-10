python3 -c "
import numpy as np
from scipy.optimize import least_squares
def f(p):
    D,B=p
    M=np.array([[6*D,6*B],[6*B,15*B]]);e=np.linalg.eigvalsh(M)+12*D
    return [10*D-12300,e[0]-18500,e[1]-27900]
r=least_squares(f,[1200,700]);print(r.x,r.fun)
def g(p):
    return f(p)[1:]
r=least_squares(g,[1200,700]);print(r.x,f(r.x))
"