import numpy as np, itertools, math
r2=math.sqrt(2)
ms=list(range(-2,3))
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
orbs=[(6,vec({0:1})),(6,vec({2:1/r2,-2:1/r2})),(-4,vec({2:1/(1j*r2),-2:-1/(1j*r2)})),(-4,vec({1:-1/r2,-1:1/r2})),(-4,vec({1:1j/r2,-1:1j/r2}))]
h=sum(e*np.outer(v,v.conj()) for e,v in orbs)
spin=[(m,s) for m in ms for s in (1,-1)]
n=10
dets=list(itertools.combinations(range(n),7))
for d in dets[:3]: print(d,[spin[i] for i in d])
# diagonal energy of each det: sum h_ii
def diag(d): return sum(h[spin[i][0]+2,spin[i][0]+2].real for i in d)
q=[d for d in dets if sum(0.5*spin[i][1] for i in d)==1.5]
print(len(q), sorted(set(round(diag(d),3) for d in q)))
