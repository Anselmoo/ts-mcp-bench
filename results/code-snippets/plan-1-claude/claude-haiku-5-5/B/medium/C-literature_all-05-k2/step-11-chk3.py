import numpy as np
d=np.load('parts.npz'); Hob,H2,H4,S2=d['Hob'],d['H2'],d['H4'],d['S2']
w,v=np.linalg.eigh(S2)
Q=v[:,np.abs(w-15/4)<1e-6]; Dd=v[:,np.abs(w-3/4)<1e-6]
for name,M in [('H2',H2),('H4',H4)]:
    e=np.linalg.eigvalsh(Q.T@M@Q)
    print(name, np.round(np.unique(np.round(e-e.min(),4)),4))
    ed=np.linalg.eigvalsh(Dd.T@M@Dd)
    print('  doublet', np.round(np.unique(np.round(ed-e.min(),4)),4))
