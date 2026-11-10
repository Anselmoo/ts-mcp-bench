cat > /tmp/a.py <<'E'
import numpy as np
from scipy.optimize import least_squares
def f(p):
    D,B=p
    w=np.linalg.eigvalsh(np.array([[-6*D,-4*B],[-4*B,15*B+6*D]]))
    return [2*D-w[0]-3600,12*D-w[0]-7870,w[1]-w[0]-16410]
r=least_squares(f,[430,700]);print(r.x,f(r.x))
E
python3 /tmp/a.py