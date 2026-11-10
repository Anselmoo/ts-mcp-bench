import numpy as np
from scipy.optimize import brentq
from fit import quartet
# Dq=0 check: quartet splitting should be 15B
v,m=quartet(0.0,1.0); print("Dq=0,B=1:",np.round(v,5),m, "diff", v[3]-v[0] if False else '')
# energies relative to 4A2 for given x=Dq/B, B=1
def nus(x):
    v,m=quartet(x,1.0)
    # identify: v sorted ascending: 4A2 (m=1), then 4T2 (m=3), then 4T1 pair
    g=v[0]
    return v[1]-g, v[2]-g, v[3]-g
for x in [0.5,1.0,1.5,2.0,2.5]:
    print(x, np.round(nus(x),4))
