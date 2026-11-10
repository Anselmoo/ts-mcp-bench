import numpy as np
from sympy.physics.wigner import wigner_3j
print(float(wigner_3j(2,2,2,0,0,0)), float(wigner_3j(2,2,0,0,0,0)))
l=2;k=2
print(float((-1)**(l-0)*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,0,0,0)*(2*l+1)))
