python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
ms=[-2,-1,0,1,2]
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=60
phis=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij')
W=np.outer(wg,np.ones(nphi))*(2*np.pi/nphi)
Y=lambda l,m,th,ph: sph_harm_y(l,m,th,ph)
D=[Y(2,m,TH,PH) for m in ms]
X=np.sin(TH)*np.cos(PH); Yc=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
Vang=X**4+Yc**4+Z**4-0.6
M=np.array([[np.sum(W*np.conj(D[a])*Vang*D[b]) for b in range(5)] for a in range(5)])
ev,vec=np.linalg.eigh(M); print(np.round(ev,5))
h1=M/(ev[3]-ev[0])*10.0
print(np.round(np.linalg.eigvalsh(h1),4))
EOF