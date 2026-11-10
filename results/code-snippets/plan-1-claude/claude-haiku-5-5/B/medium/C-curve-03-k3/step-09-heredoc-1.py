import numpy as np, itertools, math
r2=math.sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
orbs=[(6,vec({0:1})),(6,vec({2:1/r2,-2:1/r2})),(-4,vec({2:1/(1j*r2),-2:-1/(1j*r2)})),(-4,vec({1:-1/r2,-1:1/r2})),(-4,vec({1:1j/r2,-1:1j/r2}))]
h=sum(e*np.outer(v,v.conj()) for e,v in orbs)
print(np.round(h,3))
print(np.linalg.eigvalsh(h))
