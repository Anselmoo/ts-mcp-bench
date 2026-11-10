cat > /tmp/a.py <<'E'
import numpy as np
from scipy.optimize import fsolve
def f(p):
    D,B=p
    M=np.array([[-6*D,6*D],[6*D,15*B+6*D]])  # P diag: 15B+6Dq
    e=np.linalg.eigvalsh(M);g=e[0]
    return [2*D-g-15730,e[1]-g-24030]
for off in [6]:
    D,B=fsolve(f,[1900,700]);
    M=np.array([[-6*D,6*D],[6*D,15*B+6*D]]);g=np.linalg.eigvalsh(M)[0]
    print(D,B,12*D-g)
E
python3 /tmp/a.py