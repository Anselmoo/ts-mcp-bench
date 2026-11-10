import numpy as np, ts
for B,C in [(1,0),(0,1)]:
    d = ts.build(2,B,C)
    ev = np.linalg.eigvalsh(d['Hee'])
    print(B,C, sorted(set(np.round(ev-ev[0],4))))
