python3 - << 'EOF'
import numpy as np, itertools
d=np.load('<SANDBOX_TMP>/lv.npz')
Mcf,M2,M4=d['Mcf'],d['M2'],d['M4']
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]
dets=list(itertools.combinations(range(10),7))
Sz=np.array([sum(0.5*orbs[i][1] for i in dd) for dd in dets])
i3=np.where(np.isclose(Sz,1.5))[0]
print("one-body only, Sz=3/2 (Dq=1):",np.round(np.linalg.eigvalsh(Mcf[np.ix_(i3,i3)]),3))
print("full quartet (Dq=0,B=1):",np.round(np.linalg.eigvalsh((49*M2+ 0*M4)[np.ix_(i3,i3)]),3))
print("full-ee M2 eigen all:",np.round(np.unique(np.round(np.linalg.eigvalsh(M2),3)),3))
print("Mcf trace:",np.trace(Mcf), "M2 hermitian", np.allclose(M2,M2.T), np.allclose(M4,M4.T))
EOF