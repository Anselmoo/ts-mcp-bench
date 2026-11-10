from d5 import *
from scipy.optimize import least_squares
# check S2 diagonal sanity and spectrum at x=0 (free ion check: ground energy lowest)
def levels(x,B=1000.0,C=4.6):
    H=build(x*B,B,C*B)
    # Sz=1/2 subspace: states with 3 up 2 down or sym; S^2 eigen
    w,v=np.linalg.eigh(H + 1e6*(S2 - 0.75*np.eye(n)) @ np.eye(n)*0)  # no-op placeholder
    return H
H=build(0.0,1000.0,4600.0)
# doublet subspace: project onto S=1/2 by diagonalising H + mu*S2
mu=1e5
w,v=np.linalg.eigh(H+mu*S2)
S2vals=np.einsum('ia,ij,ja->a',v,S2,v)
doub=[w[i] for i in range(n) if abs(S2vals[i]-0.75)<1e-3]
print(len(doub))
