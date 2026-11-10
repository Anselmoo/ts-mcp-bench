import numpy as np
from d4 import *
B=1.0; C=4.3*B
F4=441*C/35; F2=(441*B+5*F4)/9
F={0:0.0,2:F2,4:F4}
print("F2,F4 per B:",F2,F4)
Z0=np.zeros((5,5))
for xx in [0.0, 1.0, 2.0, 3.0]:
    lv=levels(4,F,xx*h_unit*B,1)
    # h_unit has t2g=-4, eg=+6 per Dq ; pass Dq=xx*B
    print("Dq/B=",xx)
    for e_,m in lv: print("   E=%.4f  deg=%d"%(e_,m))
