import numpy as np
d=np.load('parts.npz'); Hob,H2,H4,S2=d['Hob'],d['H2'],d['H4'],d['S2']
w,v=np.linalg.eigh(S2)
Q=v[:,np.abs(w-15/4)<1e-6]
for name,M in [('H2',H2),('H4',H4),('Hob',Hob)]:
    e=np.linalg.eigvalsh(Q.T@M@Q); u,c=np.unique(np.round(e,4),return_counts=True); print(name,list(zip(u,c)))
