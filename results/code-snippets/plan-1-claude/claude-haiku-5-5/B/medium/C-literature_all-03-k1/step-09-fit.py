import numpy as np
from scipy.optimize import brentq
from d3 import levels
r=40.5/57.5   # F4/F2 giving C/B=4.5
def Fs(B):
    F2=441*B/(9-5*r); return {0:0.0,2:F2,4:r*F2}
def quartet(Dq,B):
    w=np.sort(levels(Dq,Fs(B)))
    vals=[];mult=[]
    for x in w:
        if vals and abs(x-vals[-1])<1e-6: mult[-1]+=1
        else: vals.append(x); mult.append(1)
    return vals,mult
# ground 4A2 = lowest; 4T2 mult 3 ; 4T1 mult 3 (two)
vals,mult=quartet(1.0,1.0)
print("B=1,Dq=1:",np.round(vals,5),mult)
# check independence of F4 ratio: 4P-4F separation should be 15B
