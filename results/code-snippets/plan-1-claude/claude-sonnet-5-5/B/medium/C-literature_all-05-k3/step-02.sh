python3 -c "
import numpy as np
from scipy.optimize import brentq
Dq=2155
def lo(B):
    return np.linalg.eigvalsh(np.array([[6*Dq,6*B],[6*B,15*B]]))[0]+12*Dq
B=brentq(lambda B:lo(B)-28500,300,1500);print(B)
# 2E: 9B+3C -> E(2E)=9B+3C-... approx
print((15200-9*B)/3, 15200)
"