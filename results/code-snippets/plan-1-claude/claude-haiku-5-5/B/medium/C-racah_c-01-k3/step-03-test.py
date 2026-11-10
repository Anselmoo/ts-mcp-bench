from ts import *
import numpy as np
B,C=1.0,4.0
F={0:0.0,4:63*C/5}; F[2]=49*B+F[4]/9
H,st=Hmat(F,0.0,Sz2=3)
ev=np.linalg.eigvalsh(H); print(np.round(ev-ev.min(),4))
