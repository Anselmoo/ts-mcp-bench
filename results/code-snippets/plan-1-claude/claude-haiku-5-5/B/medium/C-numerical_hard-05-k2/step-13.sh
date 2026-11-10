python3 -c "
import numpy as np
from fit import spectrum
for x in [1.5,2,2.5,3,3.5,4]:
    L=spectrum(x)
    E0=L[0][0]
    tr=[(round(E-E0,3),d,c) for E,d,c in L if d==3 and abs(abs(c)-1)<1e-3]
    print(x, 'ground deg/chi',L[0][1],L[0][2], 'T levels:',tr[:5])
"