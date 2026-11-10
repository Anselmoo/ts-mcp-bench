import numpy as np
from d4 import *
Z0=np.zeros((5,5))
# d2 free ion check
for F in [{0:0,2:1.0,4:0.625}]:
    print("d2 triplets:", [(round(a,5),m) for a,m in levels(2,{0:0,2:1,4:0.625},Z0,1)])
    print("d2 singlets:", [(round(a,5),m) for a,m in levels(2,{0:0,2:1,4:0.625},Z0,0)])
