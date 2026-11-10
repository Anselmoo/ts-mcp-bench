import numpy as np, itertools
from math import sqrt
N=10
s2=sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
h5=np.zeros((5,5),complex)
for v,e in [(vec({2:1/(1j*s2),-2:-1/(1j*s2)}),-4),(vec({1:-1/s2,-1:1/s2}),-4),(vec({1:1j/s2,-1:1j/s2}),-4),(vec({0:1}),6),(vec({2:1/s2,-2:1/s2}),6)]:
    h5+=e*np.outer(v,v.conj())
print(np.round(h5,3)); print("trace",np.trace(h5).real)
