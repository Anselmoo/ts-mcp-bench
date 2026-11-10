import numpy as np, itertools
from scipy.optimize import least_squares
from scipy.special import eval_legendre
# real d orbitals on unit sphere
n_th, n_ph = 40, 80
x_gl, w_gl = np.polynomial.legendre.leggauss(n_th)
ph = np.arange(n_ph)*2*np.pi/n_ph
ct, P = np.meshgrid(x_gl, ph, indexing='ij')
W = (np.outer(w_gl, np.ones(n_ph))*(2*np.pi/n_ph)).ravel()
st = np.sqrt(1-ct**2)
X = (st*np.cos(P)).ravel(); Y=(st*np.sin(P)).ravel(); Z=ct.ravel()
N = np.vstack([X,Y,Z]).T
c=np.sqrt(15/(4*np.pi)); c2=np.sqrt(5/(16*np.pi))
orb = [c*X*Y, c*Y*Z, c*Z*X, 0.5*c*(X**2-Y**2)*np.sqrt(1)*1.0, c2*(3*Z**2-1)]
# normalise
orb = [o for o in orb]
orb[3] = np.sqrt(15/(16*np.pi))*(X**2-Y**2)
orb[4] = np.sqrt(5/(16*np.pi))*(3*Z**2-1)
orb[0] = np.sqrt(15/(4*np.pi))*X*Y
orb[1] = np.sqrt(15/(4*np.pi))*Y*Z
orb[2] = np.sqrt(15/(4*np.pi))*Z*X
orb = np.array(orb)  # 5 x G
for i in range(5):
    print(i, np.sum(W*orb[i]**2))
cosg = N@N.T
Pk = {k: eval_legendre(k,cosg) for k in (0,2,4)}
def ang(k):
    A = np.zeros((5,5,5,5))
    for a,b,cc,d in itertools.product(range(5),repeat=4):
        rac = orb[a]*orb[cc]*W
        rbd = orb[b]*orb[d]*W
        A[a,b,cc,d] = rac@Pk[k]@rbd
    return A
A0,A2,A4 = ang(0),ang(2),ang(4)
np.save('/tmp/A.npy', np.array([A0,A2,A4]))
