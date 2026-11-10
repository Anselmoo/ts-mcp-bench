python3 -c "
from run import *
w,S=levels(0,0,1.0,0.0)
import collections
c=collections.Counter()
for e,s in zip(w,S):
    if abs(s-3.75)<1e-3: c[round(e,6)]+=1
print(sorted(c.items()))
print(sum(c.values()))
"