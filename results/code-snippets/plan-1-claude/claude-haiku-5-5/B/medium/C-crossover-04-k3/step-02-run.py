from d7 import *
import numpy as np
B,C=922.,4156.
# sanity: free ion (Dq=0) spectrum
H,states,sidx,Sz=build_H(0,B,C)
print("hermitian", np.allclose(H,H.conj().T))
ev=np.linalg.eigvalsh(H)
print(np.round(ev[:10],1))
