import numpy as np
from scipy.optimize import least_squares
obs=np.array([3600,7870,16410.])
def calc(p):
    Dq,B=p
    s=np.sqrt(225*B*B+180*B*Dq+100*Dq*Dq)
    Em=7.5*B-3*Dq-s/2; Ep=7.5*B-3*Dq+s/2
    return np.array([2*Dq-Em,12*Dq-Em,Ep-Em])
r=least_squares(lambda p:calc(p)-obs,[400,900]);print(r.x,calc(r.x))
for pair in [(0,1),(0,2),(1,2)]:
    r=least_squares(lambda p:(calc(p)-obs)[list(pair)],[400,900]);print(pair,r.x,calc(r.x))
