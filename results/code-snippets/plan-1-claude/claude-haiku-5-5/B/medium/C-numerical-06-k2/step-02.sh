
cd "$HOME" 2>/dev/null || cd /dev/shm; cat << 'EOF' > d7.py
import numpy as np
from scipy.optimize import least_squares
def bands(p):
    Dq,B=p
    H=np.array([[-8*Dq, 6*np.sqrt(3)*B],[6*np.sqrt(3)*B, 15*B]])
    Em,Ep=np.linalg.eigvalsh(H)
    return np.array([2*Dq-Em, 18*Dq-Em, Ep-Em])
obs=np.array([9180,19550,20320.])
r=least_squares(lambda p: bands(p)-obs,[900,800])
print(r.x, bands(r.x), r.fun)
EOF
python3 d7.py
