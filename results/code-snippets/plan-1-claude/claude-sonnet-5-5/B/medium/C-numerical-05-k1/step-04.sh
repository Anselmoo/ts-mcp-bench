python3 -c "
import numpy as np
from scipy.optimize import fsolve
d=[15730,24030,32750]
def E(D,B):
    w=np.linalg.eigvalsh([[-6*D,4*B],[4*B,15*B]]);g=w[0]
    return np.array([2*D-g,w[1]-g,12*D-g])
for i,j in ((0,1),(0,2),(1,2)):
  s=fsolve(lambda p:[E(*p)[i]-d[i],E(*p)[j]-d[j]],[1800,800]);print(i,j,s,E(*s))
"