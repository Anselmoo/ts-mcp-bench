python3 -c "
import numpy as np
from scipy.optimize import brentq
D=2155.5
def e(B):
    # 4T1 matrix relative to 4A2: diag 15Dq... use Tanabe-Sugano: 4T1 (F),(P)
    M=np.array([[12*D-0*0+0, 0],[0,0]])
    a=np.array([[ 6*D*0+12*D+0,0],[0,0]])
    # TS: energies from 4F ground: 4A2=-15B... use E(4T1)=roots of
    # |(3/5... 
    H=np.array([[3*D*0+ (12*D)+ 0 ,6*B],[6*B,15*B+ 0*D]])
    # relative to 4F center: 4A2=-12Dq, 4T2=-2Dq, 4T1F=+6Dq, 4T1P=15B
    H=np.array([[6*D,-6*B*0+ 6*B*0 +  (-6*B)*-1*0+6*B*0+ 0],[0,0]])
    H=np.array([[6*D,-6*B],[-6*B,15*B]])
    return np.linalg.eigvalsh(H)[0]+12*D
f=lambda B:e(B)-28500
print(brentq(f,300,1200))
B=brentq(f,300,1200)
print(B)
"
