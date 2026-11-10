import numpy as np, itertools
from scipy.optimize import least_squares
from ham import build
from ham import spin2
nel=7
basis = [sum(1<<s for s in c) for c in itertools.combinations(range(10), nel)]
idx={b:i for i,b in enumerate(basis)}
D=len(basis)
# S+ matrix
Sp=np.zeros((D,D))
for j,st in enumerate(basis):
    for o in range(5):
        up,dn=2*o,2*o+1
        if (st>>dn)&1 and not (st>>up)&1:
            sign=(-1)**bin(st & ((1<<dn)-1)).count('1')
            s1=st ^ (1<<dn); sg1=sign
            sign2=(-1)**bin(s1 & ((1<<up)-1)).count('1')
            s2=s1 | (1<<up)
            Sp[idx[s2],j]+=sg1*sign2
Sz=spin2(basis)
S2 = Sp.T@Sp + np.diag(Sz*(Sz-1)) if False else None
Sm=Sp.T
S2 = Sm@Sp + np.diag(Sz)**0 @ np.diag(Sz*(Sz+1)) - 0 # placeholder
S2 = Sm@Sp + np.diag(Sz*(Sz+1))
def levels(Dq,B,C):
    F2=49*B+7*C; F4=35*C/... if False else 5*C/7*1.0
    F4=7*C/5
    # from C=35F4/441 -> F4=441C/35 ; B=(9F2-5F4)/441 -> F2=(441B+5F4)/9
    F4=441*C/35; F2=(441*B+5*F4)/9
    _,H=build(7,Dq,0.0,F2,F4)
    w,v=np.linalg.eigh(H)
    s2=np.einsum('ij,ik,kj->j',v,S2,v)
    S=(-1+np.sqrt(1+4*s2))/2
    return w,S
import sys
