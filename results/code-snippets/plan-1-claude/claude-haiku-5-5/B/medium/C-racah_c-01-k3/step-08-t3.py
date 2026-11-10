from ts import *
from collections import Counter
for F in [{0:0,2:1,4:0},{0:0,2:0,4:1}]:
    H,st=Hmat(F,0.0,Sz2=1); ev=np.sort(np.linalg.eigvalsh(H))
    print(F, np.round(ev,4))
