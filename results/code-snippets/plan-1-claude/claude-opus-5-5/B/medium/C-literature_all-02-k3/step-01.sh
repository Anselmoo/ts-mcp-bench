python3 -c "
import numpy as np
from scipy.optimize import fsolve
def f(x):
 Dq,B,C=x
 t=np.linalg.eigvalsh([[-8*Dq-5*B,6*B],[6*B,2*Dq+4*B]]);g=t[0]
 e=np.linalg.eigvalsh([[-8*Dq+B+2*C,-2*3**.5*B],[-2*3**.5*B,12*Dq+8*B+2*C]])[0]
 return [2*Dq-8*B-g-17500,t[1]-g-25000,e-g-9748]
print(fsolve(f,[1800,600,2500]))"