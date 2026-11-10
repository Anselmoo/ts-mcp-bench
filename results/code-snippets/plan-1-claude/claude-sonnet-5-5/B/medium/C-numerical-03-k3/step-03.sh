python3 - <<'E'
import numpy as np
from scipy.optimize import fsolve
obs=[15490,24500,32330]
def lv(D,B):
    S=np.sqrt((7.5*B+6*D)**2+36*B*B);Em=7.5*B-S
    return sorted([2*D-Em,12*D-Em,2*S])
for i,j in [(0,1),(0,2),(1,2)]:
  for g in [(1000,500),(1500,800),(2000,900)]:
    s,info,ier,m=fsolve(lambda p:[lv(*p)[i]-obs[i],lv(*p)[j]-obs[j]],g,full_output=1)
    print(i,j,s,lv(*s),ier)
E