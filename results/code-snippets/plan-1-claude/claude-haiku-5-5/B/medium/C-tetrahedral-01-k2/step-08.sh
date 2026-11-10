cd <SANDBOX_TMP>/w && cat << 'EOF' > solve.py
import numpy as np
from scipy.optimize import least_squares
H0=np.load('H0.npy'); H1=np.load('H1.npy')
B0=0.1998/15.0
def lev(Dq,B):
    ev=np.sort(np.linalg.eigvalsh((B/B0)*H0 + Dq*H1))
    return ev-ev[0]
def tr(Dq,B):
    ev=lev(Dq,B)
    # distinct excited levels with degeneracy 3 (T2, T1F, T1P)
    vals=[]
    for e in ev[1:]:
        if not vals or abs(e-vals[-1])>1e-6: vals.append(e)
    return vals
obs=np.array([4070,7030,16400.])
def res(p):
    Dq,B=p
    v=tr(Dq,B)
    return [v[0]-obs[0], v[1]-obs[1], v[2]-obs[2]] if len(v)>=3 else [1e5,1e5,1e5]
for g in [(400,600),(450,700),(300,800)]:
    s=least_squares(res,g)
    print(s.x, res(s.x), tr(*s.x))
# check spectrum
EOF
python3 solve.py