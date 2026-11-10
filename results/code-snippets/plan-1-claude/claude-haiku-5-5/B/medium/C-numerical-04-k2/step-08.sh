timeout 900 python3 -c "
exec(open('ligf_run.py').read())
import numpy as np
from scipy.optimize import least_squares
def unique_levels(Dq,B):
    F=B/0.013323
    H=Hmat(Dq,F,0.625*F)
    e=np.sort(np.linalg.eigvalsh((H+H.conj().T)/2).real)
    e=e-e[0]
    # group degeneracies
    g=[];
    for x in e:
        if g and abs(x-g[-1][0])<1e-3: g[-1][1]+=1
        else: g.append([x,1])
    return g
print('check B small:', unique_levels(862,1e-3))
print('Dq=862,B=900:', unique_levels(862,900))
obs=np.array([8620.,18410.,20250.])
def model(p):
    Dq,B=p
    g=unique_levels(Dq,B)
    return np.array([g[1][0], g[2][0], g[3][0]])  # T2g, A2g, T1g(P)
sol=least_squares(lambda p: model(p)-obs, x0=[860,800], xtol=1e-12, ftol=1e-12)
print('fit (T2g,A2g,T1gP ordering):', sol.x, model(sol.x), sol.fun)
# alternative: fit using 4T1g(P) lower? try other assignment: nu1=T2g, nu2=T1gP, nu3=A2g
def model2(p):
    g=unique_levels(*p); return np.array([g[1][0], g[3][0], g[2][0]])
s2=least_squares(lambda p: model2(p)-obs, x0=[860,800])
print('alt assignment:', s2.x, model2(s2.x), s2.fun)
"