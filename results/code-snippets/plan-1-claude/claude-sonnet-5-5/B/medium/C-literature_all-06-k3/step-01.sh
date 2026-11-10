python3 -c "
import numpy as np
from scipy.optimize import brentq
D=2660
def f(B):
    M=np.array([[6*D,6*B],[6*B,15*B-6*D]])  # T1(F) at +6Dq? 
    return 0
# Tanabe-Sugano: A2 = -12Dq, T2=-2Dq, T1F=+6Dq, T1P=15B (Dq->) 
def nu2(B):
    M=np.array([[6*D,-6*B],[-6*B,15*B]])
    return min(np.linalg.eigvalsh(M))+12*D
B=brentq(lambda b:nu2(b)-32500,300,1000)
print(B)
"