python3 -c "
import numpy as np
Dq=2155
def lo(B):
    return np.linalg.eigvalsh(np.array([[6*Dq,6*B],[6*B,15*B]]))[0]+12*Dq
for B in [0,300,600,900,1500]:print(B,lo(B))
"