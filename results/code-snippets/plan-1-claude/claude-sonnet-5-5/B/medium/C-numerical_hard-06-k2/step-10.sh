cat > <SANDBOX_TMP>/d.py <<'E'
from sympy.physics.wigner import wigner_3j
from sympy import N
def c(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.0
    return float(N((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,q,mp)))
print(c(2,0,0),c(2,1,1),c(2,2,2),c(4,0,0),c(2,1,0),c(2,0,1))
E
cd <SANDBOX_TMP> && python3 d.py