import numpy as np
from scipy.special import sph_harm_y
th=np.linspace(0,np.pi,80); ph=np.linspace(0,2*np.pi,160,endpoint=False)
TH,PH=np.meshgrid(th,ph,indexing='ij')
dt=th[1]-th[0]; dp=ph[1]-ph[0]
W=np.sin(TH)*dt*dp
X=np.sin(TH)*np.cos(PH); Y=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
g=X**4+Y**4+Z**4-0.6
Yb=[sph_harm_y(2,m,TH,PH) for m in range(-2,3)]
M=np.array([[np.sum(np.conj(Yb[i])*g*Yb[j]*W) for j in range(5)] for i in range(5)])
w=np.linalg.eigvalsh(M)
print("g eig",np.round(w,4))
Mn=M*(10.0/(w[-1]-w[0]))
print("scaled eig",np.round(np.linalg.eigvalsh(Mn),4))
np.save if False else None
print(repr(np.round(Mn,6)))
