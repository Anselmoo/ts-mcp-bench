import numpy as np, itertools, pickle
from scan import levels
rs=np.round(np.arange(1.0,4.01,0.01),3)
table={}
for r in rs:
    table[r]=[(float(v),m) for v,m in levels(r,1.0)[:14]]
pickle.dump(table,open('fine.pkl','wb'))
