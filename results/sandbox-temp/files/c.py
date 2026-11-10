import numpy as np
HD,HB,HC,S=np.load('<SANDBOX_TMP>/m.npy')
H=500*HB+2000*HC
w,v=np.linalg.eigh(H)
for i in range(0,30): print(round(w[i],1), round(v[:,i]@S@v[:,i],3))
print(np.abs(H@S-S@H).max())
