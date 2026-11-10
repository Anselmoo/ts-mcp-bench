import numpy as np
from d7run import states, build
from scipy.optimize import least_squares
def sector(ev_sym):
    pass
nup = lambda s: bin(s & 0b11111).count('1')
q_idx = [i for i,s in enumerate(states) if bin(s&0b11111).count('1')==5]
d_idx = [i for i,s in enumerate(states) if bin(s&0b11111).count('1')==4]
def levels(B,C,Dq):
    H=build(B,C,Dq)
    Hq=H[np.ix_(q_idx,q_idx)]
    Hd=H[np.ix_(d_idx,d_idx)]
    eq=np.linalg.eigvalsh(Hq)
    ed=np.linalg.eigvalsh(Hd)
    return eq, ed
if __name__=='__main__':
    eq,ed=levels(1000.,4500.,0.)
    print("quartet free ion:", np.round(eq-eq[0],1))
    print("ed count", len(ed))
