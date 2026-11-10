from ts import *
F={0:0,2:0,4:0}
H,st=Hmat(F,1000.,Sz2=3)
print(np.round(np.linalg.eigvalsh(H),1))
print(np.round(np.diag(H),1))
print(st[:3])
print(np.round(PEG,3))
