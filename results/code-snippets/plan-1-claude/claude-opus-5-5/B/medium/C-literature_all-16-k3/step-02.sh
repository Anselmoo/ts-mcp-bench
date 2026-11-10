python3 -c "
import numpy as np
from scipy.optimize import least_squares,brentq
obs=np.array([7400,12660,23840])
def tr(p):
    Dq,B=p; s=np.sqrt(225*B*B+100*Dq*Dq-180*Dq*B)
    return np.array([10*Dq,7.5*B+15*Dq-s/2,7.5*B+15*Dq+s/2])
r=least_squares(lambda p:tr(p)-obs,[740,900]);Dq,B=r.x;print(r.x,tr(r.x))
def E1(C):
    M=[[8*B+2*C,2*np.sqrt(3)*B],[2*np.sqrt(3)*B,20*Dq+9*B+2*C]];return np.linalg.eigvalsh(M)[0]-15150
C=brentq(E1,100,20000);print(C,C/B)
Dq=740;B=brentq(lambda B:tr([Dq,B])[1]-12660,100,3000);print(B,tr([Dq,B]));C=brentq(E1,100,20000);print(C)
"