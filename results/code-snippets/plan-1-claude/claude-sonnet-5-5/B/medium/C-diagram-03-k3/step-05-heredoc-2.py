import re
s=open('t.py').read().split("res=[]")[0]
exec(s)
for k,R in ops.items(): print(k,abs(R.T@R-np.eye(5)).max())
H=build(0.)
for k,M in OP.items(): print(k,abs(M@H-H@M).max(),abs(H).max())
