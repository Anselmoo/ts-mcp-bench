from d3 import *
# zero-field spectrum for F2=1,F4=0 and F2=0,F4=1
for F2,F4 in [(1,0),(0,1)]:
    H=build(F2,F4,0.0); print(np.round(np.linalg.eigvalsh(H),4))
