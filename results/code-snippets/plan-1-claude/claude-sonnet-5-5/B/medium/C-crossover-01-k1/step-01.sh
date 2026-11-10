
cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B=706.;C=2734.
F4=C/35;F2=B+5*F4
Fk={0:0,2:F2,4:F4}
# F0 irrelevant (constant for fixed N)
def ck(k,m1,m2): # <2m1|C^k_{m1-m2}|2m2>
    q=m1-m2
    return float((-1)**m1*5*gaunt(2,k,2,-m1,q,m2)) 
ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0.5,-0.5)]
def g(m1,m2,m3,m4,k): # <m1 m2|1/r12|m3 m4> ; m1<-m3, m2<-m4
    if m1+m2!=m3+m4: return 0
    return (-1)**(m1-m3)*ck(k,m3,m1)*ck(k,m2,m4) if False else 0
# direct: <ab|cd> = sum_k F^k c^k(a,c) c^k(b,d)... with c^k(l m,l m')=sqrt(4pi/(2k+1))<..|Y_kq|..>
import sympy
from sympy.physics.wigner import gaunt as G
def c(k,m1,m2):
    q=m1-m2
    return float((-1)**m1*sympy.sqrt(5*5)*G(2,k,2,-m1,q,m2)) if abs(q)<=k else 0.0
def V(a,b,cc,d):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=a,b,cc,d
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0
    t=0
    for k in (2,4):
        # <m1 m2|g|m3 m4> = sum_q (-1)^q c^k(m1,m3) c^k(m4,m2)... 
        t+=Fk[k]/ (49 if k==2 else 441)*0 
    return t
E
echo