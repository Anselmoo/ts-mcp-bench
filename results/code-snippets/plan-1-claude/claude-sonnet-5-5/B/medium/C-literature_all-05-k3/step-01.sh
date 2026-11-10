python3 -c "
import numpy as np
from scipy.optimize import brentq
D=21550
def e(B):
    # 4T1 matrix relative to 4A2 (energies: 4T1(F) = 15B+... ) 
    # Tanabe-Sugano: E(4T1F)=-3Dq*... use matrix with 4A2=-12Dq
    Dq=D/10
    M=np.array([[-3*Dq+0+0,6*B],[6*B,15*B+6*Dq]])  # F: 2Dq*... placeholder
    return M
# Standard TS: 4A2=-12Dq, 4T2=-2Dq, 4T1F=3Dq+7.5B-.. matrix [[3Dq... 
def lower(B):
    Dq=D/10
    M=np.array([[6*Dq*0+ -3*Dq,6*B],[6*B,15*B+6*Dq]])
    M=np.array([[-3*Dq,6*B],[6*B,15*B+6*Dq]])
    w=np.linalg.eigvalsh(M)
    return w[0]+12*Dq
print(brentq(lambda B:lower(B)-28500,300,1500))
"