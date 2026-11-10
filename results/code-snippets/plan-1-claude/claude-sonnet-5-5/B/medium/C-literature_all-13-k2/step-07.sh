cd <SANDBOX_TMP>; python3 -c "
import a
from a import *
for flip in (0,1):
    if flip:
        for k in (2,4):
            a.C[k]=a.C[k]*np.array([[(-1)**(i-j) for j in range(5)] for i in range(5)])
    e=np.linalg.eigvalsh(a.H(0,900,3500,3));print(np.round(e-e.min()))
"