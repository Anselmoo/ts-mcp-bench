import numpy as np
from d5 import *
H=build((1.0,0,0),0.0)
w=np.linalg.eigvalsh(H)
import collections
print(collections.Counter(np.round(w,6)))
