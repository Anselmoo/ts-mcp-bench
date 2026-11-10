cat > chk.py << 'EOF'
import numpy as np
from scipy.special import sph_harm_y
from ts import Vint, orbs
from numpy.polynomial.legendre import leggauss
x,wx=leggauss(40); ph=np.linspace(0,2*np.pi,80,endpoint=False); wp=2*np.pi/80
TH,PH=np.meshgrid(np.arccos(x),ph,indexing='ij'); W=(wx[:,None]*wp*np.ones_like(TH))
def Y(l,m): return sph_harm_y(l,m,TH,PH)  # scipy: (n,m,theta,phi)
def ints(ma,mc,k,q):
    # int Y_{2,ma}^* Y_{2,mc} Y_{k,q}^* dOmega
    return np.sum(W*np.conj(Y(2,ma))*Y(2,mc)*np.conj(Y(k,q)))
def I(a,b,c,d,k):
    tot=0
    for q in range(-k,k+1):
        tot+= ints(a,c,k,q)*ints(b,d,k,-q)*(-1)**0  # Y_kq(1)Y*_kq(2) structure
    return 4*np.pi/(2*k+1)*tot
idx=lambda m:m+2
for (ma,mb,mc,md) in [(0,0,0,0),(2,0,2,0),(1,-1,1,-1),(2,0,0,2),(1,0,0,1),(2,-1,1,0)]:
    for k in (2,4):
        F={0:0,2:0,4:0}; F[k]=1
        v=Vint(idx(ma)+ (0 if True else 0),0,0,0,F) if False else None
    # map m to spin-orbital index (spin up = 2*(m+2))
    a,b,c,d=[2*(m+2) for m in (ma,mb,mc,md)]
    for k in (2,4):
        F={0:0,2:0,4:0}; F[k]=1
        print((ma,mb,mc,md),k, round(Vint(a,b,c,d,F),6), round(I(ma,mb,mc,md,k).real,6))
EOF
python3 chk.py