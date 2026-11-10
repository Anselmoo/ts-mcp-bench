import numpy as np
from fit2 import quartet_rel, triplets, spectrum
obs=np.array([6150,12400,16850,19000.])
best=[]
for Dq in range(560,761,20):
  for B in range(550,1051,50):
    for C in range(2500,5001,500):
        p=(Dq,B,C)
        qr=quartet_rel(p); q,_=spectrum(p); tr=triplets(p)-q[0]
        for k in range(len(tr)):
            pred=np.array([qr[1],qr[2],qr[3],tr[k]])
            r=np.sqrt(np.mean((pred-obs)**2))
            best.append((round(r,1),p,k,np.round(pred,0)))
best.sort(key=lambda t:t[0])
for b in best[:10]: print(b)
