cd <SANDBOX_TMP> && cat > h.py <<'E'
import numpy as np
from scipy.optimize import least_squares
from b import lev
obs=[16700,26330,35020]
def res(p):
    L=lev(p[0],p[1],4*p[1]); return [L[i][0]-L[0][0]-obs[i-1] for i in (1,2,3)]
for g in [(1800,450),(2000,500),(1500,600)]:
    r=least_squares(res,g,x_scale=[1000,300]); print(r.x,r.fun)
    L=lev(r.x[0],r.x[1],4*r.x[1]); print([(round(x-L[0][0]),d) for x,d in L][:6])
E
python3 h.py