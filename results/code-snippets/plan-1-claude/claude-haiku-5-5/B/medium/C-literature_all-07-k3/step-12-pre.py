import numpy as np
from many import *
Z=np.zeros((10,)*4,complex)
def comp(h,V): return build(h,V)
h1=H1.real
hLF,_=spin_orb(h1,np.zeros((5,5,5,5)))
_,VV0=spin_orb(np.zeros((5,5)),V0)
_,VV2=spin_orb(np.zeros((5,5)),V2)
_,VV4=spin_orb(np.zeros((5,5)),V4)
mats={}
mats['LF']=build(hLF,Z); mats['V2']=build(np.zeros((10,10)),VV2); mats['V4']=build(np.zeros((10,10)),VV4)
np.savez('pre.npz',**{k:v for k,v in mats.items()})
print('ok')
