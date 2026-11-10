import numpy as np
import ts
H=ts.build_H(0.0)
s2vals,s2vecs=np.linalg.eigh((ts.S2+ts.S2.T)/2)
W=s2vecs[:,np.abs(s2vals-8.75)<1e-6]
Hs=W.conj().T@H@W
ev,X=np.linalg.eigh((Hs+Hs.conj().T)/2)
print(np.round(ev,4))
V=W@X
chis=[np.trace(V.conj().T@Om@V) for Om in ts.Oms]
print(np.round(chis,4))
print(ts.decompose(chis))
