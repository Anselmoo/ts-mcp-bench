import numpy as np
from fit import levels
def model(p):
    Dq,B,C=p
    Esx,cl=levels(Dq,B,C)
    T=[e for e,d in cl if d==3 and e>1]
    E=[e for e,d in cl if d==2 and e>1]
    return T,E
