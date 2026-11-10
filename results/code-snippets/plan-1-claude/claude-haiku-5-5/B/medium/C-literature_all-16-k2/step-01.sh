
cat << 'EOF' > /tmp/d8.py
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
from scipy.linalg import eigh
l=2
# spin-orbitals: index = 2*(m+2)+s, s=0 up,1 down
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
n=len(orbs)
def c(k,m,mp,q):  # <l m|C^k_q|l mp>
    if m-mp!=q: return 0.0
    return float((-1)**(l-m)*np.sqrt(2*l+1)*float(wigner_3j(l,k,l,-m,q,mp)))
def Vspat(m1,m2,m3,m4,Fk):  # <m1 m2|1/r12|m3 m4>
    tot=0.0
    for k,F in Fk.items():
        for q in range(-k,k+1):
            tot+=F*c(k,m1,m3,q)*c(k,m2,m4,-q)*(-1)**q
    return tot
def build(Dq,B,C):
    F4=12.6*C; F2=49*B+7*C
    Fk={0:None,2:F2,4:F4}
    # F0 arbitrary, set 0 (doesn't affect differences)
    Fk={2:F2,4:F4}
    # one-electron cubic field: t2g -4Dq, eg +6Dq in real basis -> build in m basis via projection
    # use Ballhausen: V = Dq*(Y40 terms); use known: <m|V|m'> from real-orbital construction
    # real d orbitals in m basis: build cubic potential via Y4 cubic harmonic
    # Y4 cubic: sqrt(21/...)... use operator: V = Dq * sum_q a_q C^4_q with cubic combination
    # Cubic: V_cf = Dq*(sqrt(21/2)*... ) ; compute numerically instead via explicit angular integration
    return Fk
# numeric one-electron cubic matrix via sampling on sphere
from scipy.special import sph_harm
th=np.linspace(0,np.pi,60); ph=np.linspace(0,2*np.pi,120,endpoint=False)
TH,PH=np.meshgrid(th,ph,indexing='ij')
W=np.sin(TH)*(th[1]-th[0])*(ph[1]-ph[0])
X=np.sin(TH)*np.cos(PH); Y=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
# octahedral potential Y40+sqrt(21/...)Y44 ; cubic harmonic x^4+y^4+z^4-3/5 r^4 ∝ Y40 and Y44 combo
f=X**4+Y**4+Z**4-0.6
f=f/np.sqrt(np.sum(f**2*W))  # normalized
def Ylm(m,t,p): return sph_harm(m,2,p,t)
Yb=np.array([[Ylm(m,TH,PH)] for m in range(-2,3)])[:,0]
M=np.zeros((5,5),complex)
for i in range(5):
    for j in range(5):
        M[i,j]=np.sum(np.conj(Yb[i])*f*Yb[j]*W)
# eigen of M-like: the operator f in d-basis; octahedral: t2g eigen -4Dq, eg +6Dq ; f has eigen structure
Vop=M  # matrix of f in m-basis
w,v=np.linalg.eigh((Vop+Vop.conj().T)/2)
print("eig of f:",np.round(w,4))
EOF
python3 /tmp/d8.py
