from d7 import *
B,C=922.,4156.
H,states,sidx=build_H(0,B,C)
print("herm",np.allclose(H,H.conj().T))
ev=np.linalg.eigvalsh(H)
print(np.round(ev[:12]-ev[0],1))
