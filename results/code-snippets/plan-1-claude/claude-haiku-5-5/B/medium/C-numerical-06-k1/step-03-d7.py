import numpy as np, itertools
from scipy.special import eval_legendre
n_th, n_ph = 40, 80
x_gl, w_gl = np.polynomial.legendre.leggauss(n_th)
ph = np.arange(n_ph)*2*np.pi/n_ph
ct, P = np.meshgrid(x_gl, ph, indexing='ij')
W = (np.outer(w_gl, np.ones(n_ph))*(2*np.pi/n_ph)).ravel()
st = np.sqrt(1-ct**2)
X = (st*np.cos(P)).ravel(); Y=(st*np.sin(P)).ravel(); Z=ct.ravel()
N = np.vstack([X,Y,Z]).T
orb = np.array([np.sqrt(15/(4*np.pi))*X*Y, np.sqrt(15/(4*np.pi))*Y*Z, np.sqrt(15/(4*np.pi))*Z*X,
       np.sqrt(15/(16*np.pi))*(X**2-Y**2), np.sqrt(5/(16*np.pi))*(3*Z**2-1)])
print([round(np.sum(W*o**2),6) for o in orb])
cosg = N@N.T
Pk = {k: eval_legendre(k,cosg) for k in (0,2,4)}
A = {}
for k in (0,2,4):
    T = np.zeros((5,5,5,5))
    for a,cc in itertools.product(range(5),repeat=2):
        rac = orb[a]*orb[cc]*W
        for b,d in itertools.product(range(5),repeat=2):
            rbd = orb[b]*orb[d]*W
            T[a,cc,b,d] = rac@Pk[k]@rbd
    A[k]=T
np.save('A.npy', np.array([A[0],A[2],A[4]]))
print(A[0][0,0,0,0], A[2][3,3,3,3], A[4][3,3,3,3])
