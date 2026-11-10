import numpy as np
HD,HB,HC,S=np.load('<SANDBOX_TMP>/m.npy')
print(np.abs(HD-HD.T).max(),np.abs(HB-HB.T).max(),np.abs(S-S.T).max())
w=np.linalg.eigvalsh(S);print(np.round(sorted(set(np.round(w,6))),3))
w=np.linalg.eigvalsh(500*HB+2000*HC)
print(np.round(w[:30],1))
