cat > fit.py << 'EOF'
from ligf import *
from scipy.optimize import least_squares
obs=np.array([19720.,23260.,24980.])
def pred(p):
    Dq,B,C=p
    info=levels_assigned(Dq,B,C)
    T1=[r[0] for r in info if r[1]==3 and np.isclose(r[2],1) and np.isclose(r[3],-1)]
    T2=[r[0] for r in info if r[1]==3 and np.isclose(r[2],-1) and np.isclose(r[3],-1)]
    AE=[r[0] for r in info if r[1]==3 and np.isclose(r[2],1) and np.isclose(r[3],3)]
    return np.array([T1[0],T2[0],AE[0]])
def res(p):
    return pred(p)-obs
sol=least_squares(res,[740,860,3500],diff_step=1e-3,xtol=1e-10,ftol=1e-10)
print(sol.x, res(sol.x), pred(sol.x))
EOF
time python3 fit.py