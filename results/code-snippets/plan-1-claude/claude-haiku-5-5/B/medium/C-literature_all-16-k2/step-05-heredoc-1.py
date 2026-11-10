import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
from scipy.special import sph_harm
l=2
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
n=len(orbs)
cache={}
def c(k,m,mp,q):
    if m-mp!=q: return 0.0
    key=(k,m,mp,q)
    if key not in cache:
        cache[key]=float((-1)**(l-m)*np.sqrt(2*l+1)*float(wigner_3j(l,k,l,-m,q,mp)))
    return cache[key]
def V2(m1,m2,m3,m4,Fk):
    tot=0.0
    for k,F in Fk.items():
        for q in range(-k,k+1):
            tot+=F*c(k,m1,m3,q)*c(k,m2,m4,-q)*(-1)**q
    return tot
th=np.linspace(0,np.pi,80); ph=np.linspace(0,2*np.pi,160,endpoint=False)
TH,PH=np.meshgrid(th,ph,indexing='ij')
dt=th[1]-th[0]; dp=ph[1]-ph[0]
W=np.sin(TH)*dt*dp
X=np.sin(TH)*np.cos(PH); Y=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
g=X**4+Y**4+Z**4-0.6
Yb=[sph_harm(m,2,PH,TH) for m in range(-2,3)]
M=np.array([[np.sum(np.conj(Yb[i])*g*Yb[j]*W) for j in range(5)] for i in range(5)])
w=np.linalg.eigvalsh(M)
print("g eig",np.round(w,4))
# t2g (3 lowest) and eg (2 highest); scale so eg-t2g=10Dq, barycentre automatically -> t2g=-4, eg=+6 for Dq=1
Mn=M*(10.0/(w[-1]-w[0]))
print("scaled eig",np.round(np.linalg.eigvalsh(Mn),4))
