cd /tmp && python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
l=2; ms=[-2,-1,0,1,2]
def G(k,ma,q,mc):
    if abs(q)>k or (-ma+q+mc)!=0: return 0.0
    return float(gaunt(l,k,l,-ma,q,mc))
def ang(k,a,b,c,d):
    if a+b!=c+d: return 0.0
    s=0.0
    for q in range(-k,k+1):
        s+=((-1)**(a+q))*G(k,a,-q,c)*((-1)**b)*G(k,b,q,d)
    return 4*np.pi/(2*k+1)*s
for k in (0,2,4):
  print(k, 'direct(0,0,0,0)',ang(k,0,0,0,0),'(0,1|0,1)',ang(k,0,1,0,1), '(0,1|1,0)',ang(k,0,1,1,0), '(2,0|0,2)', ang(k,2,0,0,2),'(1,-1|-1,1)',ang(k,1,-1,-1,1))
EOF