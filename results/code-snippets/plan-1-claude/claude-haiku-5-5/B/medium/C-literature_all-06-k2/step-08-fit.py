from d3 import *
import numpy as np, time
from scipy.optimize import fsolve
def levels(H,tol=1e-3):
    w=np.sort(np.linalg.eigvalsh(H))
    out=[]
    for x in w:
        if out and abs(out[-1][0]-x)<tol: out[-1][1]+=1
        else: out.append([x,1])
    return out
t=time.time()
H=build_H(2660,700,3000)
print('time',time.time()-t)
L=levels(H)
g=L[0][0]
for e,d in L: print(round(e-g,2),d)
