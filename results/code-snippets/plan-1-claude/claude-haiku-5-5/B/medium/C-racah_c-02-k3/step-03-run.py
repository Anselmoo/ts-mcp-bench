from ts import *
import numpy as np
def levels(Dq,B,C):
    H1,V=build(Dq,B,C)
    q=basis(3); d=basis(1)
    Mq=Hmat(q,H1,V); Md=Hmat(d,H1,V)
    eq=np.sort(np.linalg.eigvalsh((Mq+Mq.conj().T)/2))
    ed=np.sort(np.linalg.eigvalsh((Md+Md.conj().T)/2))
    return eq,ed
eq,ed=levels(1000,800,3200)
print(np.round(eq-eq[0],1))
print(np.round(ed-eq[0],1))
