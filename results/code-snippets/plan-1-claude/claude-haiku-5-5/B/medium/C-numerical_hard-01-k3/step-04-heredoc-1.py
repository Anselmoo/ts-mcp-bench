import numpy as np
from scipy.special import sph_harm_y
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.full(nph,2*np.pi/nph))
def Y(k,q): return sph_harm_y(k,q,TH,PH)
cub=Y(4,0)+np.sqrt(5/14)*(Y(4,4)+Y(4,-4))
ms=[-2,-1,0,1,2]
M=np.array([[np.sum(W*np.conj(Y(2,a))*cub*Y(2,b)) for b in ms] for a in ms])
print(np.round(np.linalg.eigvalsh(M),5))
