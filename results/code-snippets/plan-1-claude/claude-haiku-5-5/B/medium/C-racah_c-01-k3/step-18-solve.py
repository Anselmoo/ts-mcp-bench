from fit import *
from scipy.optimize import least_squares
obs=dict(T2=14170., T1F=21710., T1P=33970., Ed=18540.)
def model(p):
    Dq,B,C=p
    eq,ed=levels(B,C,Dq)
    qs=np.unique(np.round(eq,3))
    T2=qs[1]; T1F=qs[2]; T1P=qs[3]
    Ed=ed[0]   # lowest doublet
    return np.array([T2,T1F,T1P,Ed])
def res(p):
    m=model(p); o=np.array([obs['T2'],obs['T1F'],obs['T1P'],obs['Ed']])
    return (m-o)/100.
x0=[1417.,600.,3000.]
sol=least_squares(res,x0,x_scale=[100,100,500],diff_step=1e-4)
print(sol.x, res(sol.x)*100, model(sol.x))
print("sol list doublets:", np.round(levels(sol.x[1],sol.x[2],sol.x[0])[1][:12],1))
