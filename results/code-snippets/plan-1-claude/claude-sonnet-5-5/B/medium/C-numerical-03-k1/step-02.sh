python3 -c "
import numpy as np
from scipy.optimize import fsolve
def f(p):
    D,B=p
    s=np.sqrt((7.5*B+6*D)**2+36*B*B);Em=7.5*B-s;Ep=7.5*B+s
    return [2*D-Em,Ep-Em,12*D-Em]
for i,j in [(0,1),(0,2),(1,2)]:
  o=[15490,24500,32330]
  for g in [(1700,800),(1000,500),(2000,300)]:
    r,info,ier,m=fsolve(lambda p:[f(p)[i]-o[i],f(p)[j]-o[j]],g,full_output=True);print(i,j,r,f(r),ier)
"