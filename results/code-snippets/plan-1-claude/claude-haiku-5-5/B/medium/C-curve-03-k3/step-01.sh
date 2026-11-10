
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from collections import Counter
# orbitals: 0..4 = t2g-like index mapping: use real d orbital set via Ylm-free approach:
# Build Coulomb matrix using Slater integrals in cubic basis via Gaunt coefficients (Racah form).
# Simpler: use Racah/Condon-Shortley via angular matrix elements computed numerically.
from fractions import Fraction
import math
from sympy.physics.wigner import wigner_3j
l=2
ml=list(range(-2,3))
# spin-orbitals: (m,s)
so=[(m,s) for m in ml for s in (1,-1)]
def gaunt_k(k,m1,m2,m3,m4):
    # <m1 m2|r12^-k|m3 m4> angular factor: sum_q (-1)^q C^k_{-m1,m3}... use Racah formula
    # e_k(m1,m3)*e_k(m2,m4) with q=m1-m3 =m4-m2
    if m1-m3 != m4-m2: return 0.0
    q=m1-m3
    s=0.0
    for kk in [k]:
        pass
    return None
def ck(l1,m1,k,q,l2,m2):
    # Gaunt-type C^k_q(l1m1,l2m2)=(-1)^m1 sqrt((2l1+1)(2l2+1)) (l1 k l2;0 0 0)(l1 k l2; -m1 q m2)
    return (-1)**m1*math.sqrt((2*l1+1)*(2*l2+1))*float(wigner_3j(l1,k,l2,0,0,0))*float(wigner_3j(l1,k,l2,-m1,q,m2))
def Vel(a,b,c,d,k):
    # <a b|V_k|c d> with orbital a,b,c,d (m values), V=sum_k ... coefficient
    # <ab|1/r12|cd>_k = F^k * (2l+1)^-2 ... use Slater: F^k coefficient times ck(a,c)ck(b,d) with sign
    q=c-a
    if q!=d-b: return 0.0
    return ck(l,a,k,q,l,c)*ck(l,b,k,-q,l,d)*(-1)**0  # approximate
# Use direct known: angular factor a_k = (sum over) -> compute 2-electron matrix via Slater-Condon with F^k and angular coefficients
def ang(m1,m2,m3,m4,k):
    # <m1 m2 | P^k | m3 m4> where P^k = sum_q (-1)^q C^k_q(1) C^k_-q(2) ; orbital integrals factor
    tot=0.0
    for q in range(-k,k+1):
        if m1-m3!=q or m4-m2!=q: 
            # need m3 = m1 - q... handle generally
            pass
    tot=0.0
    for q in range(-k,k+1):
        # electron1: m3->m1 with C^k_q: <m1|C^k_q|m3> ~ ck(l,m1,k,q,l,m3) with m1 = m3+q
        if m1 != m3+q or m2 != m4-q: continue
        tot+= (-1)**q * ck(l,m1,k,-q,l,m3)*ck(l,m2,k,q,l,m4) if False else 0
    return tot
EOF
echo skip