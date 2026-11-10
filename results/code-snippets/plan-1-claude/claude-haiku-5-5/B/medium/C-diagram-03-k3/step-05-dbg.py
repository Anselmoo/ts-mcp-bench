import numpy as np
import ts
H=ts.build_H(0.0)
print("herm err",np.abs(H-H.conj().T).max())
print("S2 eig", np.unique(np.round(np.linalg.eigvalsh((ts.S2+ts.S2.T)/2),4),return_counts=True))
for Om in ts.Oms[:2]:
    print("unitary err", np.abs(Om.conj().T@Om-np.eye(ts.N)).max(), "comm H", np.abs(Om@H-H@Om).max(), "comm S2", np.abs(Om@ts.S2-ts.S2@Om).max())
print("trace Oms", [np.round(np.trace(O),3) for O in ts.Oms])
