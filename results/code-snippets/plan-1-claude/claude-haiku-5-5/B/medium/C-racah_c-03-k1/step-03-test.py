from d3 import *
H = build_H(0.0,1.0,0.0)
print("herm", np.allclose(H,H.conj().T))
# free ion: F2 only with B=1,C=0 ; check 4F-4P spacing 15B
w = np.linalg.eigvalsh(H)
print(np.round(np.unique(np.round(w,6)),4))
