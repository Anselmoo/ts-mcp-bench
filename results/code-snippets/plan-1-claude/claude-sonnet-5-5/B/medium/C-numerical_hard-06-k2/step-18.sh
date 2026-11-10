cd <SANDBOX_TMP> && cat > i.py <<'E'
import numpy as np
from scipy.optimize import least_squares
from b import lev, HD,HB,HC,S
Dq,B=1859.95,805.53
w=np.linalg.eigvalsh(Dq*HD+B*HB+4*B*HC)
print(w[:3]-w[0])
w2=np.linalg.eigvalsh(Dq*HD+B*HB+4*B*HC+1e6*S); print(sorted(w2)[:1]-w[0])
obs=[16700,26330,35020]
def res(p,j):
    L=lev(p[0],p[1],4*p[1]); return [L[1][0]-L[0][0]-obs[0],L[2][0]-L[0][0]-obs[1],L[j][0]-L[0][0]-obs[2]]
for j in (3,4):
  for g in [(2200,500),(1800,600),(2500,350)]:
    r=least_squares(res,g,args=(j,),x_scale=[1000,300]); print(j,r.x,r.fun)
E
python3 i.py