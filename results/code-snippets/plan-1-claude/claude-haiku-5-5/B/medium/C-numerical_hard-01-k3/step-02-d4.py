import numpy as np, itertools
from scipy.optimize import brentq
from scipy.special import sph_harm
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.full(nph,2*np.pi/nph))
ms=[-2,-1,0,1,2]; l=2
def Y(k,q,T,P): return sph_harm(q,k,P,T)
# one-electron cubic operator matrix
def cub(T,P):
    return Y(4,0,T,P)+np.sqrt(5/14)*(Y(4,4,T,P)+Y(4,-4,T,P))
M=np.zeros((5,5),complex)
for i,m1 in enumerate(ms):
    for j,m3 in enumerate(ms):
        M[i,j]=np.sum(W*np.conj(Y(l,m1,TH,PH))*cub(TH,PH)*Y(l,m3,TH,PH))
ev=np.linalg.eigvalsh(M); print("unit cubic eig",np.round(ev,5))
