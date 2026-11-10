cd /; python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import pi
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
A={}
for k in (0,2,4):
    arr=np.zeros((5,5,5,5))
    for i1,m1 in enumerate(range(-2,3)):
     for i2,m2 in enumerate(range(-2,3)):
      for i3,m3 in enumerate(range(-2,3)):
       for i4,m4 in enumerate(range(-2,3)):
        tot=0.0
        for q in range(-k,k+1):
            if (-m1)-q+m3!=0 or (-m2)+q+m4!=0: continue
            g1=float(gaunt(2,k,2,-m1,-q,m3)); g2=float(gaunt(2,k,2,-m2,q,m4))
            tot+=(-1)**(m1+q+m2)*g1*g2
        arr[i1,i2,i3,i4]=4*pi/(2*k+1)*tot
    A[k]=arr
# check: F0 coefficient for <m m|m m> should be 1 (since A0 = 1 for diagonal with k=0 only)
print("A0 diag", A[0][2,2,2,2], "A2 (m=2,-2 pairs)", A[2][4,0,0,4], A[2][2,2,2,2])
import pickle
pickle.dump(A,open('/dev/null','wb')) if False else None
np.save('/dev/null',A[0]) if False else None
EOF