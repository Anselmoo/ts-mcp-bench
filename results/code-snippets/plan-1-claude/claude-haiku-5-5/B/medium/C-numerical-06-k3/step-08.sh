cd /tmp && python3 - << 'EOF'
import numpy as np
from math import sqrt
N=10
s2=sqrt(2)
import itertools
dets=[d for d in itertools.combinations(range(N),7) if sum(1 for s in d if s%2==0)==5]
idx={d:i for i,d in enumerate(dets)}
# one-body diag energies for check
def ap(ops,det):
    occ=list(det); sign=1
    for typ,i in ops:
        if typ=='a':
            if i not in occ: return None
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return sign,tuple(occ)
# orbital energies per spin-orbital: orbital o=m+2 ; t2g m-values: use real basis => energies diag in real basis; here just check one-body spectrum of Ms-space with diagonal (cubic) basis
eps=np.array([0,0,0,0,0,0,0,0,0,0.0])
# eigen of one-body H in det space using real-basis t2g/eg: build h5 quickly
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
h5=np.zeros((5,5),complex)
for v,e in [(vec({2:1/(1j*s2),-2:-1/(1j*s2)}),-4),(vec({1:-1/s2,-1:1/s2}),-4),(vec({1:1j/s2,-1:1j/s2}),-4),(vec({0:1}),6),(vec({2:1/s2,-2:1/s2}),6)]:
    h5+=e*np.outer(v,v.conj())
print("one-body orbital matrix eigen:",np.round(np.linalg.eigvalsh(h5),6))
EOF