import numpy as np
from fit2 import quartet_rel
for Dq in [600,700,800]:
  for B in [700,900]:
    for C in [3500,4500]:
        print(Dq,B,C,np.round(quartet_rel((Dq,B,C)),0))
