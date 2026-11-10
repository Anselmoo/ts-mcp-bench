python3 -c "
import numpy as np
from scipy.optimize import fsolve
def ev(Dq,B,C):
    t1=np.linalg.eigvalsh([[-8*Dq-5*B,6*B],[6*B,2*Dq+4*B]])
    e=np.linalg.eigvalsh([[-8*Dq+B+2*C,-2*np.sqrt(3)*B],[-2*np.sqrt(3)*B,12*Dq+2*C]])
    g=t1[0]
    return [2*Dq-8*B-g, t1[1]-g, e[0]-g]
f=lambda p: np.array(ev(*p))-[17500,25000,9748]
s=fsolve(f,[1800,600,3000]);print(s,ev(*s))
"