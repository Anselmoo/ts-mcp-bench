cat > run2.py << 'EOF'
import numpy as np
from scipy.optimize import least_squares
from fit2 import quartet_rel, triplets, spectrum
def r3(p):
    qr=quartet_rel(p)
    return np.array([qr[1]-6150, qr[2]-12400, qr[3]-16850])
sols=[]
for Dq0 in [500,700,900]:
  for B0 in [500,800,1000]:
    for C0 in [3000,4000,5000]:
        s=least_squares(r3,[Dq0,B0,C0],x_scale=[100,100,500],diff_step=1e-4)
        sols.append((s.cost,tuple(np.round(s.x,2)),np.round(s.fun,1)))
sols.sort(key=lambda t:t[0])
for x in sols[:6]: print(x)
EOF
python3 run2.py