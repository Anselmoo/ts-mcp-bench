import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=922.;C=4156.
F4=63*C/5;F2=49*B+5*F4
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,-m1,m1-m2,m2)*wigner_3j(2,k,2,0,0,0))
# two-electron d2 triplet-F vs P check: <2,1|g|2,1> direct-exchange for Ms=1 d2 state m=3: |2,1>
def gg(m1,m2,m3,m4): 
    if m1+m2!=m3+m4:return 0
    return sum(F*c(k,m1,m3)*c(k,m4,m2) for k,F in((2,F2),(4,F4)))
# triplet M_L=3 state of d2 (same spin): E = <21|g|21> - <21|g|12>
print(gg(2,1,2,1)-gg(2,1,1,2), "expected F2 energy 3F: F0-8B")
print(gg(2,1,2,1),gg(2,1,1,2))
