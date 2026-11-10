import sys; sys.path.insert(0,'.')
from ts import *
Dq,B=2000.,800.
ev=singlets(Dq,B)
g=groups(ev)
print([(round(e-ev[0],0),m) for e,m in g])
