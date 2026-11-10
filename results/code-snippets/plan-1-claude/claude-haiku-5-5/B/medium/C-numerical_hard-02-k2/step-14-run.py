import numpy as np
from d4 import *
B=1.0; C=4.3*B
F4=441*C/35; F2=(441*B+5*F4)/9
F={0:0.0,2:F2,4:F4}
obs=np.array([22900,23730,24580.])
res=[]
for xx in np.arange(1.0,8.01,0.25):
    lv=levels(4,F,xx*h_unit,1)
    E0=lv[0][0]
    exc=[(round(e_-E0,4),m) for e_,m in lv[1:]]
    print("x=%.2f ground deg=%d"%(xx,lv[0][1]), [ (a,b) for a,b in exc[:6]])
