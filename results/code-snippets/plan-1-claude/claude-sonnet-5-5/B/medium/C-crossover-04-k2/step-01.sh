
cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B=922.;C=4156.
F4=C/35;F2=B+5*F4  # Racah-normalized: F2/49 units
F={2:F2*49,4:F4*441}
ms=range(-2,3)
def ck(k,m1,m2): # <l m1|C^k|l m2> times, l=2
    return float((-1)**m1*gaunt(2,k,2,-m1,m1-m2,m2)*5) if False else float((-1)**m1*5*gaunt(2,k,2,-m1,m1-m2,m2))
def c(k,m1,m2): return ck(k,m1,m2)
orb=[(m,s) for m in ms for s in (0.5,-0.5)]
idx={o:i for i,o in enumerate(orb)}
def g(m1,m2,m3,m4): # <m1 m2|1/r12|m3 m4> 
    t=0
    for k in (2,4):
        q=m1-m3
        if q!=m4-m2: continue
        t+=F[k]/ (49 if k==2 else 441)*0  # placeholder
    return t
from math import *
Fk={2:F2,4:F4}  # F^k/(49 or 441) = Racah F_k
def V(m1,m2,m3,m4):
    t=0
    for k in (0,2,4):
        if m1+m2!=m3+m4: continue
        a=c(k,m1,m3)*c(k,m4,m2)
        fk={0:0,2:F2,4:F4}[k]
        t+=fk*a
    return t
# c(k,m1,m3)=<m1|C|m3>; <12|g|34> = sum ck(m1,m3) ck(m4,m2) F^k  with F^k = Fk_racah*49/441
# fix scaling
def V(m1,m2,m3,m4):
    t=0
    if m1+m2!=m3+m4: return 0
    for k,fk in ((2,F2*49),(4,F4*441)):
        t+=fk*c(k,m1,m3)*c(k,m4,m2)
    return t
E
echo ok