import numpy as np, itertools
exec(open('chk2.py').read().split('for nel in (2,3)')[0])
for lab,V in (('F2',V2),('F4',V4)):
    dets,H=build(5,V)
    up=[i for i,d in enumerate(dets) if all(so[k][1]==+1 for k in d)]
    print(lab, np.round(H[np.ix_(up,up)].real,6))
