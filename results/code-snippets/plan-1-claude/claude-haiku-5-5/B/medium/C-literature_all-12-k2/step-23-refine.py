import numpy as np
from scipy.optimize import least_squares
from fit2 import quartet_rel, triplets, spectrum
obs=np.array([6150,12400,16850,19000.])
def pred(p,k):
    qr=quartet_rel(p); q,_=spectrum(p); tr=triplets(p)-q[0]
    return np.array([qr[1],qr[2],qr[3],tr[k]])
for k in [0,1,2,3]:
    f=lambda p: pred(p,k)-obs
    s=least_squares(f,(675,800,3500),diff_step=1e-4,bounds=([500,400,1500],[900,1300,7000]))
    print("k",k,"Dq,B,C",np.round(s.x,0),"resid",np.round(s.fun,0),"rms",round(np.sqrt(np.mean(s.fun**2)),1))
