from fast import *
obs=np.array([19720.,23260.,24980.])
def pred(p):
    info=levels(*p)
    T1=[r[0] for r in info if r[1]==3 and np.isclose(r[2],1) and np.isclose(r[3],-1)]
    T2=[r[0] for r in info if r[1]==3 and np.isclose(r[2],-1) and np.isclose(r[3],-1)]
    AE=[r[0] for r in info if r[1]==3 and np.isclose(r[2],1) and np.isclose(r[3],3)]
    return np.array([T1[0],T2[0],AE[0]])
sol=least_squares(lambda p: pred(p)-obs,[740,860,3500],diff_step=1e-3,xtol=1e-9,ftol=1e-9,max_nfev=60)
print('Dq,B,C=',sol.x, 'resid',pred(sol.x)-obs)
