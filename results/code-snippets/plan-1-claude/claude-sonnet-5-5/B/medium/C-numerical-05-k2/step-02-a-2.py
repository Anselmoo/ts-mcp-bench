import numpy as np
from scipy.optimize import fsolve
def lev(D,B):
    M=np.array([[-6*D,6*D],[6*D,15*B+6*D]]); return np.linalg.eigvalsh(M)
def f(p):
    D,B=p;e=lev(D,B);g=e[0]
    return [2*D-g-15730,e[1]-g-24030]
D,B=fsolve(f,[1900,700]);g=lev(D,B)[0]
print(D,B,12*D-g)
