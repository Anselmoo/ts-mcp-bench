from d5 import *
from scipy.optimize import least_squares
def spectrum(x,B=1000.0,C=4.6):
    H=build(x*B,B,C*B)
    mu=1e5
    w,v=np.linalg.eigh(H+mu*S2)
    S2v=np.einsum('ia,ij,ja->a',v,S2,v)
    E=np.array([w[i] for i in range(n) if abs(S2v[i]-0.75)<1e-3])
    return np.sort(E)
E=spectrum(0.0)
print(len(E), E[:5]-E[0])
