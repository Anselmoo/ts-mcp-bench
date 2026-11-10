mkdir -p /work && cat > /work/d2.py << 'EOF'
import numpy as np, itertools
from functools import lru_cache
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve

l=2
ms=list(range(-2,3))
@lru_cache(None)
def G(l1,l2,l3,m1,m2,m3):
    return float(gaunt(l1,l2,l3,m1,m2,m3))

def Ysum(ma,mc,k,q):  # ∫ Y_a* Y_c Y_kq* dΩ  (Y* of kq)
    # Y_a* = (-1)^ma Y_{l,-ma}; Y_kq* = (-1)^q Y_{k,-q}
    if mc-ma!=q: return 0.0
    return (-1)**(ma+q)*G(l,l,k,-ma,mc,-q)
def Yprod(mb,md,k,q):  # ∫ Y_b* Y_d Y_kq
    if md-mb!=q: return 0.0
    return (-1)**mb*G(l,l,k,-mb,md,q)

# cubic one-electron operator O = Y40 + sqrt(5/14)(Y44+Y4-4): <a|O|c> = ∫Y_a* O Y_c
def Oint(ma,mc):
    tot=0.0
    for (k,q,coef) in [(4,0,1.0),(4,4,np.sqrt(5/14)),(4,-4,np.sqrt(5/14))]:
        # ∫ Y_a* Y_kq Y_c = (-1)^ma ∫Y_{l,-ma} Y_kq Y_{l,mc}
        if mc-ma+q!=0: continue
        tot+=coef*(-1)**ma*G(l,4,l,-ma,q,mc)
    return tot
Om=np.array([[Oint(a,c) for c in ms] for a in ms])
ev=np.linalg.eigvalsh(Om)
print("cubic eigen (raw):",np.round(ev,6))
# t2g: m=±2,±1,0 combos; with proper normalization spacing e_eg - e_t2g
e_t2g=ev[0]; e_eg=ev[-1]
print("spacing ratio check", ev)

def ang(a,b,c,d,k):
    # <ab|1/r12|cd> angular part for orbitals a(m),b(m),c,d ; returns coefficient multiplying F^k
    s=0.0
    for q in range(-k,k+1):
        s+=Ysum(a,c,k,q)*Yprod(b,d,k,q)
    return 4*np.pi/(2*k+1)*s

def Vint(a,b,c,d,F):
    return sum(F[k]*ang(a,b,c,d,k) for k in (0,2,4))

# spin-orbitals: index = 2*i + s, s=0 up, 1 down; i index of ms
def build(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9
    F={0:0.0,2:F2,4:F4}
    # scale cubic op so that t2g=-4Dq, eg=+6Dq
    # eigen of Om: t2g triplet, eg doublet; spacing = 10Dq
    s=10*Dq/(ev[-1]-ev[0]) if False else None
    return F
EOF
cd /work && python3 d2.py