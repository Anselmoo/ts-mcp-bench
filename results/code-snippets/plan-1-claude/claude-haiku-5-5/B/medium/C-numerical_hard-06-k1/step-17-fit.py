from d6 import *
from scipy.optimize import least_squares
obs=np.array([16700,26330,35020.])
def res(p):
    x,B=p
    T,_=Ts(x)
    pred=np.array(T[:3])*B
    return (pred-obs)/obs
s=least_squares(res,[2.3,800],x_scale=[0.1,50])
print(s.x, s.x[0]*s.x[1], res(s.x))
x,B=s.x; T,_=Ts(x); print(np.array(T[:3])*B)
