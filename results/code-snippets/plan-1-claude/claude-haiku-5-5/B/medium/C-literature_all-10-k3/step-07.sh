cat > solve.py << 'EOF'
import numpy as np
from scipy.optimize import fsolve
from fit import levels, cluster
def bands(Dq,B):
    e=levels(Dq,B)
    g=cluster(e)
    E0=g[0][0]
    tr=[(a-E0,n) for a,n in g[1:] if n==3]
    return tr
def resid(x):
    tr=bands(*x)
    return [tr[0][0]-16611, tr[1][0]-23529]
for guess in [(2000,600),(2500,650),(3000,700),(1800,550)]:
    x=fsolve(resid,guess,full_output=True)
    print(guess, x[0], resid(x[0]), bands(*x[0])[:3])
EOF
python3 solve.py