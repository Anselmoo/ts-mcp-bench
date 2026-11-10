from fit2 import spec, obs
import numpy as np
from scipy.optimize import brentq
for Dq in [433.0]:
    for idx_ in [1,2]:
        f=lambda B: spec(Dq,B)[idx_]-obs[idx_]
        Bs=np.linspace(300,1500,121); v=[f(b) for b in Bs]
        print(idx_, [ (round(Bs[i]),round(v[i])) for i in range(0,120,20)])
        
