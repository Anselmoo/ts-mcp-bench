python3 -c "
import numpy as np
from scipy.optimize import brentq
D=2155.
f=lambda B:15*D+7.5*B-0.5*np.sqrt(225*B**2+100*D**2-180*D*B)-28500
B=brentq(f,300,1200);print(B)
# 2E: 9B+3C-90B^2/(10Dq)
C=(15200-9*B+ 90*B**2/(10*D))/3;print(C,C/B)
"
