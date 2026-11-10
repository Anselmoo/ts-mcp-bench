import numpy as np
from d4 import *
F={0:0.0,2:1.0,4:0.625}
# Racah B,C in terms of F2,F4
# check: compute free-ion energies to get B,C
H=build({0:0,2:1.0,4:0.625}).toarray()
Hs=H[np.ix_(sel,sel)]; S2s=S2.toarray()[np.ix_(sel,sel)]
Ht=Hs+1e4*S2s
e,v=np.linalg.eigh(Ht)
# triplet energies
trip=[]
for i in range(len(e)):
    s2=v[:,i]@S2s@v[:,i]
    if abs(s2-2)<1e-3: trip.append(e[i])
print("free ion triplet energies (F2=1,F4=0.625):", np.round(sorted(set(np.round(trip,6))),6))
quart=[e[i] for i in range(len(e)) if abs(v[:,i]@S2s@v[:,i]-0)<1e-3]
print("singlet ion count", sum(abs(v[:,i]@S2s@v[:,i])<1e-3 for i in range(len(e))))
