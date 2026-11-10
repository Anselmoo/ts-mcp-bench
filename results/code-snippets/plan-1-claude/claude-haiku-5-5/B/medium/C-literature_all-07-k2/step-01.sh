
cat << 'EOF' > /tmp/d5.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
from scipy.linalg import eigh
l=2; ms=list(range(-2,3))
# spin orbitals: (m, s) s=+1/2 index
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
N=len(orbs)
# Gaunt-based Slater expansion: <a b|1/r|c d> = sum_k F^k * a_k
from functools import lru_cache
@lru_cache(None)
def G(k,m1,m3,q):
    # angular integral int Y_{2m1}^* Y_{k q}^* Y_{2 m3}  (convert to real using sympy gaunt for complex harmonics)
    return complex(gaunt(l,k,l,-m1,q,m3)) * (-1)**m1  # approximate; checked below
def ak(k,m1,m3,m2,m4):
    # <m1 m2|C|m3 m4> angular: sum_q (-1)^q <m1|C^k_q|m3><m2|C^k_-q|m4>
    s=0
    for q in range(-k,k+1):
        s+= (-1)**q * G(k,m1,m3,q)*G(k,m2,m4,-q)
    return s*4*np.pi/(2*k+1)
def Vee(F):
    # build two-electron antisymmetrized tensor
    V=np.zeros((N,N,N,N))
    for i,(m1,s1) in enumerate(orbs):
        for j,(m2,s2) in enumerate(orbs):
            for kk,(m3,s3) in enumerate(orbs):
                for ll,(m4,s4) in enumerate(orbs):
                    if s1!=s3 or s2!=s4: continue
                    val=0
                    for k,Fk in zip((0,2,4),F):
                        val+=Fk*ak(k,m1,m3,m2,m4).real
                    V[i,j,kk,ll]=val
    return V
EOF
python3 -c "
from sympy.physics.wigner import gaunt
print(float(gaunt(2,0,2,0,0,0)), float(gaunt(2,2,2,0,0,0)))"
