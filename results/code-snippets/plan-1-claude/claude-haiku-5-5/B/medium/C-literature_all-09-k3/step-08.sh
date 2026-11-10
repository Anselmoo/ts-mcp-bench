python3 -c "
from ligf import *
import numpy as np
w,ss=build(0,1.0,0.0)
S=np.round((-1+np.sqrt(1+4*ss))/2*2)/2
for s in sorted(set(S)):
    sel=np.isclose(S,s)
    vals=np.round(w[sel]-w.min(),3)
    u,c=np.unique(vals,return_counts=True)
    print('S=',s,'levels (B units, count):',list(zip(u,c)))
"