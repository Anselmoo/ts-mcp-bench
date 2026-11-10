
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from math import comb
# orbitals: m in -2..2 ; spin-orbital index (m,s)
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]
N=len(orbs)
B=1.0; C=3699/784
F4=441*C/35; F2=(441*B+5*F4)/9
# Slater-Condon via Gaunt-type angular coefficients computed numerically
from sympy.physics.wigner import wigner_3j
def ak(k,m1,m2,m3,m4):
    # <m1 m3|r12^-k|m2 m4> angular part = (-1)^... use 3j formula with q=m1-m3=m4-m2
    # ak = (2l+1)^2 * (l k l;0 0 0)^2 * sum over... use standard via Gaunt
    from sympy.physics.wigner import gaunt
    return 0
# Use Condon-Shortley: <ab|1/r12|cd> = sum_k f_k(abcd) F^k with f_k = (2l+1)^2 (l k l;000)^2 * (l k l; -ma mc ... )
l=2
def f(k,ma,mb,mc,md):
    # direct-type: <m_a m_b | r^k | m_c m_d>, a,b electron1,2 ; c->a, d->b
    if ma-mc != md-mb: return 0.0
    q=ma-mc
    if abs(q)>k: return 0.0
    w0=float(wigner_3j(l,k,l,0,0,0))
    w1=float(wigner_3j(l,k,l,-ma,mc,0))*(-1)**(0)
    w2=float(wigner_3j(l,k,l,-mb,md,0))
    return (-1)**(ma+mb)*(2*l+1)*w0*float(wigner_3j(l,k,l,-ma,mc,-q))*float(wigner_3j(l,k,l,-mb,md,q))*(-1)**(0)
EOF
python3 -c "import sympy; print(sympy.__version__)"
