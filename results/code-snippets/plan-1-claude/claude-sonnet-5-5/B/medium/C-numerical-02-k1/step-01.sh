python3 -c "
import numpy as np
from scipy.optimize import least_squares
def lv(p):
    D,B=p
    w=np.linalg.eigvalsh([[-6*D,6*D],[6*D,15*B+6*D]]);E0=w[0]
    return [2*D-E0,12*D-E0,w[1]-E0]
obs=[9460,20160,21160]
for g in [(1000,900),(1100,800)]:
    r=least_squares(lambda p:np.array(lv(p))-obs,g);print(r.x,lv(r.x))
"