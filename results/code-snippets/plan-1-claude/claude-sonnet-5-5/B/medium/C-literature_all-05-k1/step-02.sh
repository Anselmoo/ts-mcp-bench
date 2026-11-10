python3 -c "
import numpy as np
from scipy.optimize import brentq
D=2155.
e=lambda B:np.linalg.eigvalsh(np.array([[6*D,-6*B],[-6*B,15*B]]))[0]+12*D
for B in [0,500,700,900,1200,2000]:print(B,e(B))
B=brentq(lambda B:e(B)-28500,300,3000);print(B, 15200)
# C from 2E = 9B+3C - 90B^2/(10Dq)... 
for C in [(15200-(9*B-90*B**2/(10*D)*0))/3]:print(C)
"
