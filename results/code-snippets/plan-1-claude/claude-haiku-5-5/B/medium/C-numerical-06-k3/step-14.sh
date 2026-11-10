cd /tmp && python3 - << 'EOF'
import numpy as np, itertools
from math import sqrt
N=10; s2=sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
h5=np.zeros((5,5),complex)
for v,e in [(vec({2:1/(1j*s2),-2:-1/(1j*s2)}),-4),(vec({1:-1/s2,-1:1/s2}),-4),(vec({1:1j/s2,-1:1j/s2}),-4),(vec({0:1}),6),(vec({2:1/s2,-2:1/s2}),6)]:
    h5+=e*np.outer(v,v.conj())
print("h5 eig",np.round(np.linalg.eigvalsh(h5),3))
# 2-electron antisym within 5-dim: pair operator
pairs=list(itertools.combinations(range(5),2))
M=np.zeros((10,10),complex)
for i,(a,b) in enumerate(pairs):
    for j,(c,d) in enumerate(pairs):
        # <ab|h⊗1+1⊗h|cd> antisym
        val = h5[a,c]*(b==d) + h5[b,d]*(a==c) - h5[a,d]*(b==c) - h5[b,c]*(a==d)
        M[i,j]=val
print("2e eig",np.round(np.linalg.eigvalsh(M),3))
EOF