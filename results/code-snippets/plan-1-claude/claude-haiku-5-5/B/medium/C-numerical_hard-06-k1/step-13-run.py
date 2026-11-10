from d6 import *
for x in [1.0,2.0,2.5,3.0,3.5,4.0,4.5,5.0]:
    lv=singlet_levels(x,1.0)
    e0=lv[0][0]
    print(x,[(round(e-e0,4),m) for e,m in lv if e-e0<60][:8])
