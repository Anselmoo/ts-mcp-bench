import numpy as np
from scipy.optimize import brentq
D,B=1875,583.3333;e0=-18416.67
def g(C):
    M=np.array([[-8*D+B+2*C,-2*5**.5*B],[-2*5**.5*B,2*D-8*B+2*C]])
    return np.linalg.eigvalsh(M)[0]-e0-9748
C=brentq(g,0,6000);print(C,C/B)
