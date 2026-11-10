
cd <SANDBOX_TMP>/d7 && python3 -c "
from d7 import *
print(list(A.items())[:5]); print(max(abs(v) for v in A.values()))
H,st,si=build_H(0,922.,4156.); print(abs(H).max(), np.linalg.eigvalsh(H)[:5], np.linalg.eigvalsh(H)[-3:])
print(sph_harm(0,2,PH,TH)[0,0])
"