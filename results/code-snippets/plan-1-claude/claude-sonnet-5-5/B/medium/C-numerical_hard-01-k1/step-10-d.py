from a import *
obs=[18850,19750,20560]
def r(Dq,B):
    L=levels(B,4.7*B,Dq); g=L[0][0]
    e=[x-g for x,d in L[1:]]
    return sum((e[i]-obs[i])**2 for i in range(3)),e[:3]
best=None
for Dq in range(2120,2260,10):
  for B in range(760,860,10):
    v=r(Dq,B)
    if best is None or v[0]<best[0]: best=(v[0],Dq,B,v[1])
print(best)
_,D0,B0,_=best
for Dq in [D0-10+2*i for i in range(11)]:
  for B in [B0-10+2*i for i in range(11)]:
    v=r(Dq,B)
    if v[0]<best[0]: best=(v[0],Dq,B,v[1])
print(best)
