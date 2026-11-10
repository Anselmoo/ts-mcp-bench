cd /tmp && python3 - <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
l=2
so=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
N=len(so)
def C(k,q,ma,mc):
    if ma-q!=mc: return 0.0
    red=(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    return (-1)**(l-ma)*float(wigner_3j(l,k,l,-ma,q,mc))*red
# check: <m|C^0_0|m> should be 1 (since C^0 = identity)
print([round(C(0,0,m,m),4) for m in range(-2,3)])
# check C^2 reduced: sum_m,m' |<m|C^2_0|m'>|^2 should be (2l+1)^2 * ... ; compare to known <l||C^k||l>^2 /(2l+1)?? just print
print([[round(C(2,0,a,b),4) for b in range(-2,3)] for a in range(-2,3)])
EOF