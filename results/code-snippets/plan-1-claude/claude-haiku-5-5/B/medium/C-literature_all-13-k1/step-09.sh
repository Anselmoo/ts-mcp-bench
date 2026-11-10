python3 -c "
from d7 import *
print('k0 m=0', 4*pi*gnt(2,0,0,0,2,0)*gnt(2,0,0,0,2,0))
print('ang k2 (0,0;0,0)', ang(2,0,0,0,0), 'expect 25*(2 2 2;000)^2=', 25*2/35)
print('ang k4 (0,0;0,0)', ang(4,0,0,0,0), 'expect 25*(2 4 2;000)^2=', 25*(2/35*0+0))
from sympy.physics.wigner import wigner_3j
print(float(wigner_3j(2,2,2,0,0,0))**2*25, float(wigner_3j(2,4,2,0,0,0))**2*25)
print('ang k4', ang(4,0,0,0,0))
"