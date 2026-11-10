sed -i 's/F={2:441\*B+63\*C,4:441\*C\/35.0}/F={2:49*B+7*C,4:441*C\/35.0}/' d7.py && grep -n "F={" d7.py && python3 -c "
from d7 import *
import numpy as np
H,S2=build(0,100,0)
w,v=np.linalg.eigh(H+1e5*S2)
res={}
for vec in v.T:
    s2=vec@S2@vec; S=(-1+np.sqrt(1+4*s2))/2
    k=(round(2*S)/2, round(vec@H@vec,3)); res[k]=res.get(k,0)+1
print(sorted(res.items()))
"