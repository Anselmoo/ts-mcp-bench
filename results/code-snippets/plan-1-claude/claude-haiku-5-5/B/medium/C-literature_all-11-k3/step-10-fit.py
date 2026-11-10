from d6 import *
from scipy.optimize import fsolve
def levels(Dq,B):
    w=singlet_levels(Dq,B,4.5*B)
    g=groups(w); g0=g[0][0]
    return [x-g0 for x,n in g if n==3]
def res(p):
    t=levels(*p)
    return [t[0]-16474., t[1]-25381.]
sol=fsolve(res,[1800.,900.],xtol=1e-10)
print("Dq,B=",sol, "residual",res(sol))
print("levels:",[round(x) for x in levels(*sol)[:4]])
print("Dq/B=",sol[0]/sol[1])
