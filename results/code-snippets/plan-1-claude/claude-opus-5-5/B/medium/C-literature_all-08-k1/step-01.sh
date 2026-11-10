cat << 'EOF' > /tmp/a.py
import numpy as np
from scipy.optimize import fsolve
s2,s6=np.sqrt(2),np.sqrt(6)
def lo(M):return np.linalg.eigvalsh(M)[0]
def f(x):
    Dq,B=x;C=(23370-10*B)/5
    T1=np.array([[-25*B+6*C-10*Dq,3*s2*B,C],[3*s2*B,-16*B+7*C,-3*s2*B],[C,-3*s2*B,-25*B+6*C+10*Dq]])
    T2=np.array([[-17*B+6*C-10*Dq,-s6*B,C],[-s6*B,-22*B+5*C,-s6*B],[C,-s6*B,-17*B+6*C+10*Dq]])
    return [lo(T1)+35*B-19180, lo(T2)+35*B-22130]
x=fsolve(f,[700,700]);print(x,(23370-10*x[1])/5,f(x))
EOF
python3 /tmp/a.py