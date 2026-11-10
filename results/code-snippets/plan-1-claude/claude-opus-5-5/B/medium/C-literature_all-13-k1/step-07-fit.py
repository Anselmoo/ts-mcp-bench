from d7 import *
from scipy.optimize import least_squares
obs=np.array([7150,15200,19200,21130.])
def calc(p):
    L=levels(*p); g=L[4][0][0]
    q=[e-g for e,l in L[4]]
    d=[e-g for e,l in L[2] if l=='T1']
    q4={l+str(i):0 for i,l in enumerate([])}
    t2=[e-g for e,l in L[4] if l=='T2'][0]; a2=[e-g for e,l in L[4] if l=='A2'][0]; t1p=[e-g for e,l in L[4] if l=='T1'][1]
    return np.array([t2,a2,t1p,d[1]]),L,g
r=least_squares(lambda p: calc(p)[0]-obs,[800,880,3800])
print(r.x, calc(r.x)[0], calc(r.x)[0]-obs)
c,L,g=calc(r.x)
for k in L:
    for e,l in L[k]: print(k,l,round(e-g))
