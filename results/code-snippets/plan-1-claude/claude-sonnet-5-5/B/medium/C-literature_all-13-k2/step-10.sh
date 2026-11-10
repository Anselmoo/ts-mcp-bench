cd <SANDBOX_TMP>; python3 -c "
from a import *
print(C[4].round(3))
V=sum(np.einsum('ac,db->abcd',C[k],C[k]) for k in (2,4))
print(abs(V-V.transpose(1,0,3,2)).max(), abs(V-V.transpose(2,3,0,1).conj()).max())
"