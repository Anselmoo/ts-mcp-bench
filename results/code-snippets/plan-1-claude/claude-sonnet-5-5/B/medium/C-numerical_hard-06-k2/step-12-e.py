import numpy as np
HD,HB,HC,S=np.load('m.npy')
w=np.linalg.eigvalsh(500*HB+2000*HC+1e4*S)
out=[]
for x in w:
    if out and abs(x-out[-1][0])<1e-3: out[-1][1]+=1
    else: out.append([x,1])
print([(round(a,1),b) for a,b in out if a<5000])
