python3 -c "
import numpy as np
from scipy.optimize import fsolve
def f(p):
    D,B=p
    w=np.linalg.eigvalsh([[-6*D,6*B],[6*B,15*B+6*D]])
    return [2*D-w[0]-4400,w[1]-w[0]-15500]
print(fsolve(f,[400,700]))"