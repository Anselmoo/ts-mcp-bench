import numpy as np, itertools
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
N=10
def Ang(mi,mk,K,q):
    if -mi+mk-q!=0 or abs(q)>K: return 0.0
    return (-1)**(mi)*((-1)**q)*float(gaunt(2,2,K,-mi,mk,-q))
# check Ang for K=2 symmetry: sum over q of A(mi,mk)*A(mj,ml) etc
for mi,mk in [(1,1),(2,-2),(0,0),(1,-1)]:
    print(mi,mk,[round(Ang(mi,mk,2,q),4) for q in range(-2,3)])
