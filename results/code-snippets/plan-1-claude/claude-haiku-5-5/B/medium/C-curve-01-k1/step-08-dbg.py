import numpy as np, sys
sys.path.insert(0,'.')
from d4 import *
ops={'E':np.eye(D),'C3':rot((1,1,1),2*np.pi/3),'C2z':rot((0,0,1),np.pi),'C4z':rot((0,0,1),np.pi/2),"C2'":rot((1,0,0),np.pi)}
for k,U in ops.items():
    print(k, np.round(np.trace(U),4), np.allclose(U@U.conj().T,np.eye(D)))
print('commute S2', np.abs(S2@Hee-Hee@S2).max(), np.abs(S2@Hcf-Hcf@S2).max())
print('commute rot H', np.abs(ops['C3']@Hcf-Hcf@ops['C3']).max(), np.abs(ops['C3']@Hee-Hee@ops['C3']).max())
