
cat << 'EOF' > /tmp/d5.py
import numpy as np, itertools
from scipy.optimize import least_squares
# orbitals: index 0..4 = t2g (xy,xz,yz) ->0,1,2 ; eg (z2,x2-y2)->3,4 ; spin up = o, down = o+5
orbs=range(10)
def orb(i): return i%5
def spin(i): return i//5
basis=[c for c in itertools.combinations(range(10),5)]
# restrict to Ms=3/2 : nup - ndown = 3 -> nup=4, ndown=1
sub=[c for c in basis if sum(1 for i in c if spin(i)==0)-sum(1 for i in c if spin(i)==1)==3]
idx={c:k for k,c in enumerate(sub)}
# Slater-Condon-free approach: build full two-electron matrix via second quantization
# Coulomb: sum_{ijkl} <ij|1/r12|kl> a+_i a+_j a_l a_k /2 ; need Slater integrals F0,F2,F4 with Gaunt coefficients for d (l=2)
from sympy.physics.wigner import gaunt
import sympy
def ang(m1,m2,m3,m4,k):
    # <m1 m2|C^k|m3 m4> style: sum_q (-1)^q <l||C^k||l>... use Gaunt-based formula
    # angular factor a_k(m1,m2,m3,m4)= sum_q (-1)^q <2 m1|C^k_q|2 m3><2 m2|C^k_-q|2 m4>
    tot=0.0
    for q in range(-k,k+1):
        # <l m|C^k_q|l m'> = (-1)^{l-m} * 3j(l k l;-m q m') * (2l+1)? use gaunt: <Y_l1m1|Y_kq|Y_l2m2> ~ 
        def C(m,mp,q):
            # Gaunt-based: C^k_q matrix elt = (-1)^m sqrt((2l+1)(2l'+1)) 3j(l k l';0 0 0) 3j(l k l'; -m q m')
            return float((-1)**m*sympy.sqrt(5*5)*sympy.physics.wigner.wigner_3j(2,k,2,0,0,0)*sympy.physics.wigner.wigner_3j(2,k,2,-m,q,mp))
        tot+=(-1)**q*C(m1,m3,q)*C(m2,m4,-q)
    return tot
def mls(i): return [None]
# orbital m values: t2g xy(m=-2?) use real-ish: use complex basis m=-2..2 instead. Simplify: work in complex m basis
EOF
echo