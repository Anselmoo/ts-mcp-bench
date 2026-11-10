import numpy as np, itertools
d=np.load('<SANDBOX_TMP>/lv.npz')
Mcf,M2,M4=d['Mcf'],d['M2'],d['M4']
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]
dets=list(itertools.combinations(range(10),7))
Sz=np.array([sum(0.5*orbs[i][1] for i in dd) for dd in dets])
i3=np.where(np.isclose(Sz,1.5))[0]
for Dq,B,C in [(1000,0,0),(0,1000,0),(1000,1000,0),(0,0,1000),(1000,0,1000)]:
    F4=12.6*C; F2=49*B+5*F4/9
    Hm=Dq*Mcf+F2*M2+F4*M4
    print((Dq,B,C), np.round(np.linalg.eigvalsh(Hm[np.ix_(i3,i3)]),1))
