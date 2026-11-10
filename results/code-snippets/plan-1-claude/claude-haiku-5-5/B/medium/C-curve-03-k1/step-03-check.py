from d7 import *
# d2 check: 3P - 3F = 15B  with Racah B=(9F2-5F4)/441
import numpy as np
for F2,F4 in [(1.0,0.0),(1.0,0.6)]:
    F={0:0.0,2:F2,4:F4}
    H,nup=build(F,0.0,nel=2)
    ev=np.linalg.eigvalsh(H)
    print(F2,F4,np.round(np.unique(np.round(ev,6)),6))
    B=(9*F2-5*F4)/441; C=35*F4/441
    print('B',B,'C',C)
