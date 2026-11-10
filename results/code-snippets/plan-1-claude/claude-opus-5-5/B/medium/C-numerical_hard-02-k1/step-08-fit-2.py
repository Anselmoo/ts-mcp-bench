from d4 import levels
import numpy as np
def terms(Dq,B):
    t,q=levels(Dq,B,4.3*B); g=[]
    for x in t:
        if g and abs(x-g[-1][0])<1e-2: g[-1][1]+=1
        else: g.append([x,1])
    return [(x-g[0][0],n) for x,n in g], q[0]-g[0][0]
print([(round(x),n) for x,n in terms(0,600)[0]])
obs=np.array([22900,23730,24580])
best=None
for Dq in np.arange(1800,4001,50):
  for B in np.arange(200,1001,25):
    g,q=terms(Dq,B)
    if g[1][1]==3 and g[1][0]<1: continue
    e=np.array([x for x,n in g[1:4]])
    r=np.sum((e-obs)**2)
    if best is None or r<best[0]: best=(r,Dq,B,[(round(x),n) for x,n in g[:5]],q)
print(best)
