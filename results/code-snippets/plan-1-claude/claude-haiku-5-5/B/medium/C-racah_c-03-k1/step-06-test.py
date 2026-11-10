from d3 import *
H = build_H(0.0,1.0,0.0)
print("herm", np.allclose(H,H.conj().T))
w = np.linalg.eigvalsh(H)
print(np.round(np.unique(np.round(w,6)),4))
