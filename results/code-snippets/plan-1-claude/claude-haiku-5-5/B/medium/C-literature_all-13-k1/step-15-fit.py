import numpy as np
from scipy.optimize import least_squares
from an import levels
obs=dict(T2q=7150,A2q=15200,T1q2=19200,T1d2=21130)
def pred(p):
    Dq,B,C=p
    L=levels(Dq,B,C)
    g=L[0][0]
    # quartets
    q=[x for x in L if x[1]==1.5]
    d=[x for x in L if x[1]==0.5]
    T2q=[x for x in q if x[2]==3 and x[3]==-1]
    A2q=[x for x in q if x[2]==1 and x[3]==-1]
    T1q=[x for x in q if x[2]==3 and x[3]==1]
    T1d=[x for x in d if x[2]==3 and x[3]==1]
    return dict(T2q=T2q[0][0]-g, A2q=A2q[0][0]-g, T1q2=T1q[1][0]-g, T1d2=T1d[1][0]-g,
                gs=q[0][0]-g)
def res(p):
    P=pred(p)
    return [P[k]-obs[k] for k in obs]
sol=least_squares(res,[800,900,3500],x_scale=[100,100,300],diff_step=1e-3)
print(sol.x, res(sol.x))
print(pred(sol.x))
