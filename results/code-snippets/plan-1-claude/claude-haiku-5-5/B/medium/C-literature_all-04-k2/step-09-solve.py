import numpy as np
from scipy.optimize import least_squares
from fit import spectrum
def ident(Dq,B,C):
    q,d=spectrum(Dq,B,C)
    A2=q[0][0]
    t=[e for e,m in q[1:] if m==3]
    T2,T1F=t[0],t[1]
    E2=[e for e,m in d if m==2]
    E2e=min(E2,key=lambda e:abs(e-(A2+14300)))
    return T2-A2,T1F-A2,E2e-A2
def res(p):
    Dq,B,C=p
    a,b,c=ident(Dq,B,C)
    return [a-17500,b-23800,c-14300]
sol=least_squares(res,[1750,700,3000],x_scale=[1000,500,2000])
print(sol.x, sol.fun)
print("pred", ident(*sol.x))
