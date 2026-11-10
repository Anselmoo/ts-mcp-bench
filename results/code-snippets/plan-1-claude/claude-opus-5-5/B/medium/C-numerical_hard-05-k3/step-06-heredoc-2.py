import numpy as np
H1,HB,HC,S2=np.load('mats.npy')
# free ion check: d6 terms with B=1,C=4.5
w=np.linalg.eigvalsh(HB+4.5*HC); w-=w.min()
print(np.unique(np.round(w,4)))
print(np.allclose(H1,H1.T),np.allclose(HB,HB.T))
