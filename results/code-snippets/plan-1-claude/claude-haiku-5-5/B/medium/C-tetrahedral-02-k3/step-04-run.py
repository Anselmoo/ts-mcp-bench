from d3 import *
for F2,F4 in [(1,0),(0,1)]:
    H=build(F2,F4,0.0); print(F2,F4,np.round(np.linalg.eigvalsh(H),4))
