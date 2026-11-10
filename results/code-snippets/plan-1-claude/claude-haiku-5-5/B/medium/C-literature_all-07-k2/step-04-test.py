import numpy as np, collections
from d5 import *
# Ms=3/2 subspace: 4 up,1 down
sub=[i for i,d in enumerate(dets) if sum(orbs[x][1] for x in d)==3]
H=build((1.0,0,0),0.0)
Hs=H[np.ix_(sub,sub)]
w=np.linalg.eigvalsh(Hs.real)
print(len(sub), collections.Counter(np.round(w,6)))
