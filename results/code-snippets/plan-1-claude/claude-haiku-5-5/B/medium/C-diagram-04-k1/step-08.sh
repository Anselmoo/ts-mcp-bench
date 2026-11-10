python3 -c "
import numpy as np
import ts
from ts import *
# N=2 check of Coulomb: 3P-3F should be 15B (Racah), with F0 excluded
idx2=[n for n in range(D) if bin(n).count('1')==2]
H2n = np.asarray(H2.tocsr()[idx2][:,idx2].todense())
S2n = np.asarray(S2.tocsr()[idx2][:,idx2].todense())
w,V=np.linalg.eigh((H2n+H2n.T)/2)
Sv=np.real(np.einsum('ij,ik,kj->j',V.conj(),S2n,V))
import collections
for e,s in zip(w,Sv):
    pass
groups=collections.defaultdict(list)
for e,s in zip(np.round(w,4),np.round(Sv,3)): groups[(s,e)].append(1)
for k in sorted(groups): print(k, len(groups[k]))
"