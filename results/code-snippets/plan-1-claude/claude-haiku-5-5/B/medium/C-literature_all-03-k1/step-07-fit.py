import numpy as np
from scipy.optimize import brentq
from d3 import levels
np.set_printoptions(precision=4,suppress=True)
r=40.5/57.5   # F4/F2 giving C/B=4.5
def spectrum(Dq,B):
    # F2 chosen so that Racah B = B: B=(9F2-5F4)/441 with F4=r F2 -> F2=441B/(9-5r)
    F2=441*B/(9-5*r); F={0:0.0,2:F2,4:r*F2}
    w=np.unique(np.round(levels(Dq,F),6))
    return w
def quartet_nu(Dq,B):
    F2=441*B/(9-5*r); F={0:0.0,2:F2,4:r*F2}
    w=levels(Dq,F)
    w=np.sort(w)
    # distinct levels with multiplicities
    vals=[];mult=[]
    for x in w:
        if vals and abs(x-vals[-1])<1e-6: mult[-1]+=1
        else: vals.append(x); mult.append(1)
    return vals,mult
# test with B=1, Dq=1 
vals,mult=quartet_nu(1.0,1.0)
print(vals,mult)
