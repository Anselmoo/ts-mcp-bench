import numpy as np
H1,HB,HC,S2=np.load('mats.npy')
w=np.linalg.eigvalsh(HB+4.5*HC); w-=w.min()
print(np.unique(np.round(w,4)))
w=np.linalg.eigvalsh(H1); print(np.unique(np.round(w-w.min(),4)))
