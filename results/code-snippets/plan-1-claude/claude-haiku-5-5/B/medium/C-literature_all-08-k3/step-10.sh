python3 -c "
from d5 import *
for B,C in [(1000.,0.),(0.,1000.)]:
    w,s2=levels(0.0,B,C)
    s6=w[np.abs(s2-35/4)<1e-6]; q=w[np.abs(s2-15/4)<1e-6]
    print(B,C,'sext',np.round(s6-s6[0],3)[:3],'quart',sorted(set(np.round(q-s6[0],3))))
"