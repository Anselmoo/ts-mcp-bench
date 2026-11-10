
cd $TMPDIR && python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.
    return float(((-1)**m1)*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def two(a,b,c,d,F):
    if a[1]!=c[1] or b[1]!=d[1]: return 0.
    if a[0]+b[0]!=c[0]+d[0]: return 0.
    return sum(F[k]*C[(k,a[0],c[0])]*C[(k,d[0],b[0])] for k in (0,2,4))
print(two((2,1),(1,1),(2,1),(1,1),{0:0,2:49,4:0}), two((2,1),(1,1),(1,1),(2,1),{0:0,2:49,4:0}))
print(C[(2,2,1)],C[(2,1,2)])
EOF
