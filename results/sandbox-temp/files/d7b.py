exec(open('d7.py').read().split("f=lambda")[0])
import numpy as np
def g(Dq):
    o=lows(Dq); q=o[1.5]; d=o[0.5]
    dd=[x for x in d if np.min(np.abs(q-x))>1e-6]
    return dd[0]-q[0]
from scipy.optimize import brentq
for Dq in [1500,1800,2000]: print(Dq,g(Dq))
r=brentq(g,1000,3000,xtol=1e-9); print(r,r/B)
