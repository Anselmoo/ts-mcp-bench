
cd $TMPDIR && cat << 'EOF' > fit.py
from lev import levels
import numpy as np
from scipy.optimize import least_squares
obs=np.array([22640,22930,25080])
def f(p,show=False):
    r=levels(*p)
    d=[x for x in r[1:] if abs(x[1]-0.75)<0.1]
    if show: print([np.round(x,1) for x in r[:10]])
    return np.array([x[0] for x in d[:3]])-obs
s=least_squares(f,[2500,600]); print(s.x, s.fun); f(s.x,True)
EOF
python3 fit.py
