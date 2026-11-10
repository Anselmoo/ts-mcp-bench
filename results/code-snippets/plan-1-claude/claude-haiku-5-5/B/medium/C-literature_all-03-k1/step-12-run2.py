import numpy as np
from scipy.optimize import brentq, least_squares
from d3 import quartet
obs=np.array([12300,18500,27900.])
def pred(p):
    Dq,B=p
    v,m=quartet(Dq,B)
    g=v[0]; return np.array([v[1]-g, v[2]-g, v[3]-g])
# pure least squares over Dq,B
res=least_squares(lambda p: pred(p)-obs, x0=[1200,800], xtol=1e-12, ftol=1e-12)
print("LSQ Dq,B =",res.x, "pred", pred(res.x), "resid", pred(res.x)-obs)
# alt: fit nu1 and nu3 exactly (Dq from nu1), B from nu3 
def fx(x):  # x=Dq/B from nu3/nu1
    v,m=quartet(x,1.0); g=v[0]; return (v[3]-g)/(v[1]-g)-27900/12300
x3=brentq(fx,0.5,3.0); v,m=quartet(x3,1.0); B3=12300/(v[1]-v[0]); print("nu1+nu3 fit: Dq/B",x3,"B",B3,"Dq",x3*B3)
def fx2(x):
    v,m=quartet(x,1.0); g=v[0]; return (v[2]-g)/(v[1]-g)-18500/12300
