cat > /tmp/a.py <<'E'
import numpy as np
from scipy.optimize import least_squares
def lv(D,B):
    S=np.sqrt((7.5*B+6*D)**2+36*B*B);Em=7.5*B-S
    return np.array([2*D-Em,12*D-Em,2*S]),
obs=np.array([15490,24500,32330])
def f(p,perm):
    D,B=p;S=np.sqrt((7.5*B+6*D)**2+36*B*B);Em=7.5*B-S
    v=np.array([2*D-Em,12*D-Em,2*S]);v=np.sort(v) if perm else v
    return v-obs
for g in [(1700,700),(900,600),(2000,800)]:
    r=least_squares(f,g,args=(1,));print(r.x,r.fun)
E
python3 /tmp/a.py