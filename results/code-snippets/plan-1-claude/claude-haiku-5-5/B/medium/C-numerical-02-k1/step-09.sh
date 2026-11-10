python3 -c "
from run import *
import collections
w,S=levels(0,0,1.0,0.0)
print(collections.Counter(np.round(S,3)))
"