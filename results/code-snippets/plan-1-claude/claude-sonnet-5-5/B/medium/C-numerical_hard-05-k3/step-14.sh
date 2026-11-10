cd <SANDBOX_TMP> && python3 -c "
from a import *
for k in (2,4):
  for a in ms:
    for b in ms:
      if abs(c[k,a,b]-(-1)**(a-b)*c[k,b,a])>1e-9: print('asym',k,a,b,c[k,a,b],c[k,b,a])
print(c[2,2,0],c[2,0,2],c[2,-2,0],c[2,-1,1],c[2,1,-1])
"