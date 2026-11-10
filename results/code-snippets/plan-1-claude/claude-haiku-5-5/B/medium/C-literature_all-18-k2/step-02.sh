cat << 'EOF' > /tmp/d8.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq, least_squares
l=2
ms=[-2,-1,0,1,2]
# spin orbitals: (m,s), s=+1/-1
so=[(m,s) for s in (1,-1) for m in ms]
idx={o:i for i,o in enumerate(so)}
def Cmat(k,q,m,mp):
    # <l m|C^k_q|l mp>
    if m-(-q)... if False else None
EOF
echo