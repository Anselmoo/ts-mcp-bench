cat > /tmp/a.py <<'E'
import numpy as np
from scipy.optimize import fsolve
def lv(D,B):
    M=np.array([[-6*D,-4*D],[-4*D,15*B]])
    return np.linalg.eigvalsh(M)
def f(x):
    D,B=x;e=lv(D,B);return [2*D-e[0]-17500,e[1]-e[0]-25000]
D,B=fsolve(f,[1800,650]);e=lv(D,B)
C=(9748+e[0]-6*D-5*B)/2
print(D,B,C,e)
E
python3 /tmp/a.py