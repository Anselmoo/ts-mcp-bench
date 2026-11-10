
mkdir -p ~/w && cd ~/w && cat << 'EOF' > d8.py
import numpy as np
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
from scipy.special import sph_harm
l=2
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
n=len(orbs)
def c(k,m,mp,q):
    if m-mp!=q: return 0.0
    return float((-1)**(l-m)*np.sqrt(2*l+1)*float(wigner_3j(l,k,l,-m,q,mp)))
def V2(m1,m2,m3,m4,Fk):
    tot=0.0
    for k,F in Fk.items():
        for q in range(-k,k+1):
            tot+=F*c(k,m1,m3,q)*c(k,m2,m4,-q)*(-1)**q
    return tot
# one-electron cubic operator
th=np.linspace(0,np.pi,80); ph=np.linspace(0,2*np.pi,160,endpoint=False)
TH,PH=np.meshgrid(th,ph,indexing='ij')
dt=th[1]-th[0]; dp=ph[1]-ph[0]
W=np.sin(TH)*dt*dp
X=np.sin(TH)*np.cos(PH); Y=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
g=X**4+Y**4+Z**4-0.6
Yb=[sph_harm(m,2,PH,TH) for m in range(-2,3)]
M=np.array([[np.sum(np.conj(Yb[i])*g*Yb[j]*W) for j in range(5)] for i in range(5)])
w=np.linalg.eigvalsh(M)
delta=w[-1]-w[0]  # eg-t2g
# check degeneracy
print("g eig",np.round(w,4))
h1=M*(10.0/ (w[-1]-w[0]) )  # eg-t2g=10 Dq with Dq=1 scale, barycentre zero
# convention: t2g=-4, eg=+6 (for Dq=1); h1 has eig t2g=-6? check
w2=np.linalg.eigvalsh(h1); print("h1 eig (Dq=1 units)",np.round(w2,4))
EOF
python3 d8.py
