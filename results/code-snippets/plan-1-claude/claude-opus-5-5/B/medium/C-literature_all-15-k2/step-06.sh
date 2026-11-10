python3 - << 'EOF' 2>&1 | tail -5
import numpy as np
# quartet analytic d7: energies rel 4T1F
def q(Dq,B):
    S=np.sqrt(225*B**2+100*Dq**2+180*Dq*B)
    return 5*Dq-7.5*B+0.5*S, 15*Dq-7.5*B+0.5*S, S
from scipy.optimize import fsolve
for pair in [(0,2),(1,2)]:
    obs=np.array([8480,16305,20360])
    f=lambda p: [q(*p)[i]-obs[i] for i in pair]
    s=fsolve(f,[850,900]); print(pair,s,q(*s))
EOF