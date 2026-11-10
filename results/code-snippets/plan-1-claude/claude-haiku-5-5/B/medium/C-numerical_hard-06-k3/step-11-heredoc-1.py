import sys; sys.path.insert(0,'.')
from ts import *
from scipy.optimize import least_squares
def model(p):
    Dq,B=p
    ev=singlets(Dq,B)
    g=groups(ev,1e-2)
    g0=g[0][0]
    t=[e-g0 for e,m in g if m==3 and e-g0>1]
    return t[:3], [e-g0 for e,m in g if e-g0>1][:6]
target=np.array([16700,26330,35020.])
def res(p):
    t,_=model(p)
    return np.array(t)-target
sol=least_squares(res,[2000,800],x_scale=[1000,300],diff_step=1e-3)
print(sol.x, res(sol.x), model(sol.x))
