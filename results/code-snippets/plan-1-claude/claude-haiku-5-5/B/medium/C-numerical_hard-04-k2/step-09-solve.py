import numpy as np, itertools, pickle
from scan import levels
obs=np.array([29360,29620,31640.])
rs=np.round(np.arange(0.8,4.01,0.05),3)
table={}
for r in rs:
    L=levels(r,1.0)
    table[r]=[(v,m) for v,m in L[:12]]
pickle.dump(table,open('table.pkl','wb'))
print("done")
