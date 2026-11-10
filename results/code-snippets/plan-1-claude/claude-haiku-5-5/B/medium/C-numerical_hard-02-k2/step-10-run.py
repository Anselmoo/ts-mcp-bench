import numpy as np
from d4 import *
# free ion, F2=1, F4=0.625 : check ratios
t = triplet_levels({0:0.0,2:1.0,4:0.625}, np.zeros((5,5)))
print("free-ion triplets (F2=1,F4=.625):", np.round(t,4))
