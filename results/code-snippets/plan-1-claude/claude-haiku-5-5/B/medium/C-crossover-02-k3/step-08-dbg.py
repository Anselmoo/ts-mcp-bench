import numpy as np
H2=np.load("H2.npy"); S2=np.load("S2.npy")
print(np.round(np.linalg.eigvalsh(S2),3)[:20], np.unique(np.round(np.linalg.eigvalsh(S2),3)))
