python3 -c "
import numpy as np
from fit import spectrum
from scipy.optimize import brentq
def levels(x):
    L=spectrum(x); E0=L[0][0]
    return [(E-E0,d,c) for E,d,c in L]
def trip(x):
    out=[]
    for e,d,c in levels(x)[1:]:
        if d==3 and abs(abs(c)-1)<1e-3: out.append((e,c))
    return out
for x in np.arange(1.8,2.4,0.1):
    t=trip(x)
    print(round(x,2), [round(a,3) for a,_ in t[:4]], [c for _,c in t[:4]], 'r2=%.4f r3=%.4f'%(t[1][0]/t[0][0], t[2][0]/t[0][0]))
"