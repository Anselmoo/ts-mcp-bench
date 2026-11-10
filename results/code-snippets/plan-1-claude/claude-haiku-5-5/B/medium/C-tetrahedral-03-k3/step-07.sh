cd <SANDBOX_TMP>/w && python3 -c "
from d8 import *
for F2,F4 in [(1,0),(0,1)]:
    H=H_matrix(0.0,F2,F4)
    print(F2,F4,np.round(np.linalg.eigvalsh(H),5))
print(np.round(f2[2,2,2,2],5), 2/35*25, np.round(f4[2,2,2,2],5))
"