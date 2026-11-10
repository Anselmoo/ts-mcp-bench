import sys; sys.path.insert(0,'.')
from d4 import *
B=float(sys.argv[1]);Dq=float(sys.argv[2])
g=levels(Dq,B,4.3*B); E0=g[0][0]
for x,n in g[:8]: print(round(x-E0,1),n)
