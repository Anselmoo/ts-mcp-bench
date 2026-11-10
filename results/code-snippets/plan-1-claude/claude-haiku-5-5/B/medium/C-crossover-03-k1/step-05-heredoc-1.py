import numpy as np
from scipy.special import sph_harm_y
nt,nph=60,120
x,w=np.polynomial.legendre.leggauss(nt)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*2*np.pi/nph
Y=lambda l,m: sph_harm_y(l,m,TH,PH)
ms=[-2,-1,0,1,2]
for c in [np.sqrt(5/14), np.sqrt(10/7)]:
    v=Y(4,0)+c*(Y(4,4)+Y(4,-4))
    M=np.array([[np.sum(W*np.conj(Y(2,a))*v*Y(2,b)) for b in ms] for a in ms])
    print(c, np.round(np.linalg.eigvalsh((M+M.conj().T)/2),6))
