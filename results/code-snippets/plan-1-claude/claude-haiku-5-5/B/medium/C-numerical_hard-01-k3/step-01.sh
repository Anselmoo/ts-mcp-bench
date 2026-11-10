
cat << 'EOF' > /tmp/d4.py
import numpy as np, itertools
from scipy.optimize import least_squares
from scipy.special import sph_harm
# quadrature on sphere
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.full(nph,2*np.pi/nph))
ms=[-2,-1,0,1,2]; l=2
def Y(k,q,T,P): return sph_harm(q,k,P,T)  # scipy: sph_harm(m,n,azimuth,polar)
def A(k,q,m1,m3):
    return np.sum(W*np.conj(Y(l,m1,TH,PH))*np.conj(Y(k,q,TH,PH))*Y(l,m3,TH,PH))
# one-electron cubic field: find V in m-basis with eg=+6Dq, t2g=-4Dq (per Dq unit)
# V = a*(Y40 + sqrt(5/14)(Y44+Y4-4)) ; compute matrix of Re-combos
def Vop(a_):
    M=np.zeros((5,5),complex)
    for i,m1 in enumerate(ms):
        for j,m3 in enumerate(ms):
            val=0
            # real combination Y40 + sqrt(5/14)(Y44+Y4-4)
            f=lambda T,P: np.conj(Y(l,m1,T,P))*(Y(4,0,T,P)+np.sqrt(5/14)*(Y(4,4,T,P)+Y(4,-4,T,P)))*Y(l,m3,T,P)
            val=np.sum(W*f(TH,PH))
            M[i,j]=val
    return M
M=Vop(1)
ev=np.linalg.eigvalsh(M)
print("eig of unit cubic op",np.round(ev,4))
EOF
python3 /tmp/d4.py
