cd ~ 2>/dev/null || cd .; python3 - << 'EOF'
import numpy as np
from scipy.optimize import least_squares, brentq
def E(p):
    Dq,B,C=p; g=-12*Dq-8*B
    t2=-2*Dq-8*B-g
    M=np.array([[-2*Dq+4*B,6*B],[6*B,8*Dq-5*B]])
    t=np.linalg.eigvalsh(M)-g
    N=np.array([[-12*Dq+2*C,-2*np.sqrt(3)*B],[-2*np.sqrt(3)*B,8*Dq+B+2*C]])
    e=np.linalg.eigvalsh(N)[0]-g
    return np.array([t2,t[0],t[1],e])
obs=np.array([7400,12660,23840,15150])
r=least_squares(lambda p:E(p)-obs,[740,950,3500]);print(r.x,E(r.x))
Dq=740;B=14300/15
C=brentq(lambda c:E([Dq,B,c])[3]-15150,1000,8000);print(C,E([Dq,B,C]))
EOF