import sys; sys.path.insert(0,'<SANDBOX_TMP>')
from run2 import doublets
import numpy as np
from scipy.optimize import minimize_scalar
obs=np.array([22640,22930,25080.])
def res(x):
    E=doublets(x,B=1000.0); L=(E-E[0])/1000.0
    Bfit=obs/L[1:4]
    return np.std(Bfit)/np.mean(Bfit), Bfit.mean()
r=minimize_scalar(lambda x: res(x)[0], bounds=(3.05,3.15), method='bounded', options={'xatol':1e-5})
x=r.x; sd,B=res(x)
print("x=",x,"B=",B,"Dq=",x*B, "spread",sd)
# final energies check with fitted B, C=4.6B
E=doublets(x,B=B,C=4.6*B); print(np.round(E-E[0],0)[:5])
