from d6 import *
# free-ion check: d2 3F->3P = 15B
H,S2=build(0,77,50.4,nel=2)
print('S2 eig check', np.unique(np.round(np.linalg.eigvalsh(S2),3)))
lv=singlet_levels(0.0,1.0)
print('free-ion d6 singlets (B=1):',[(round(e,4),m) for e,m in lv][:12])
