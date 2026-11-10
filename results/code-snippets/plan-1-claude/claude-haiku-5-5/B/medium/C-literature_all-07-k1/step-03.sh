mkdir -p /w && cat > /w/ligand.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.special import sph_harm
from scipy.optimize import fsolve
from functools import lru_cache
l=2; ms=list(range(-2,3)); nM=5
@lru_cache(None)
def G(m1,k,q,m3):  # int Y_{2,m1}^* Y_{k,q}^* Y_{2,m3}
    return float((-1)**(m1+q)*gaunt(2,k,2,-m1,-q,m3))
def a(k,m1,m2,m3,m4):
    if abs(m1-m3)>0 and False: pass
    s=0.0
    for q in range(-k,k+1):
        if abs(q)>0 and False: pass
        s+= float(gaunt(2,k,2,-m1,-q,m3)*gaunt(2,k,2,-m2,q,m4))*(-1)**(m1+q+m2)
    return 4*np.pi/(2*k+1)*s
# check a0
print("a0 check", a(0,2,-1,2,-1), a(0,2,-1,-1,2), a(0,2,2,2,2))
# Slater-integral expansion: <m1 m2|V|m3 m4> = F0 a0 + F2 a2 + F4 a4
A={}
for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
    A[(m1,m2,m3,m4)]=[a(k,m1,m2,m3,m4) for k in (0,2,4)]
# one-electron cubic field
th,wt=np.polynomial.legendre.leggauss(40)
phis=np.linspace(0,2*np.pi,80,endpoint=False)
Lvecs=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
def Ymat():
    M=np.zeros((5,5),complex)
    T,P=np.meshgrid(np.arccos(th),phis,indexing='ij')
    W=np.outer(wt,np.ones(len(phis)))*(2*np.pi/len(phis))
    V=np.zeros_like(T)
    for L in Lvecs:
        x=np.sin(T)*np.cos(P); y=np.sin(T)*np.sin(P); z=np.cos(T)
        c=x*L[0]+y*L[1]+z*L[2]
        V+= 35*c**4/8-30*c**2/8+3/8   # P4 Legendre
    for i,m1 in enumerate(ms):
        for j,m2 in enumerate(ms):
            Y1=sph_harm(m1,2,P,T); Y2=sph_harm(m2,2,P,T)
            M[i,j]=np.sum(np.conj(Y1)*V*Y2*W)
    return M
h=Ymat()
ev=np.linalg.eigvalsh(h)
print("raw eig",ev)
EOF
cd /w && python3 ligand.py