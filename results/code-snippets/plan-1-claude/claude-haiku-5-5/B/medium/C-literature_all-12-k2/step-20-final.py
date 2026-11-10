import numpy as np
from scipy.optimize import least_squares
from fit2 import quartet_rel, triplets, spectrum
def rq(p):
    qr=quartet_rel((p[0],p[1],0.0))
    return np.array([qr[1]-6150, qr[2]-12400, qr[3]-16850])
for x0 in [(600,800),(650,800),(700,900)]:
    s=least_squares(rq,x0,diff_step=1e-5)
    print("3-band fit Dq,B:",np.round(s.x,1),"resid",np.round(s.fun,1))
def r2(p):
    qr=quartet_rel((p[0],p[1],0.0)); return np.array([qr[1]-6150, qr[2]-12400])
s2=least_squares(r2,(650,800),diff_step=1e-5); print("2-band (4T2,4A2) Dq,B:",np.round(s2.x,1),np.round(s2.fun,1))
Dq,B=s2.x
qr=quartet_rel((Dq,B,0)); print("predicted quartets:",np.round(qr,0))
# doublets vs C
for C in np.arange(2000,6001,250):
    q,_=spectrum((Dq,B,C)); tr=triplets((Dq,B,C))-q[0]
    print(C, np.round(tr[:6]).astype(int))
