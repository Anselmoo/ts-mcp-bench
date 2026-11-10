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
h=np.zeros((N,N),complex)
for o1 in range(5):
    for o2 in range(5):
        for sg in range(2): h[2*o1+sg,2*o2+sg]=h5[o1,o2]
print(np.round(np.linalg.eigvalsh(h),3))
dets=[d for d in itertools.combinations(range(N),7) if sum(1 for s in d if s%2==0)==5]
print(len(dets), dets[:3])
EOF