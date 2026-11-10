from ts import *
import numpy as np
h=onebody()
V2=Vtensor(2); V4=Vtensor(4)
D,Hcf=build(7,h,np.zeros((N,)*4))
_,H2=build(7,np.zeros((N,N)),V2)
_,H4=build(7,np.zeros((N,N)),V4)
ind={d:i for i,d in enumerate(D)}
n=len(D)
Sz=np.zeros((n,n)); Sp=np.zeros((n,n))
for j,occ in enumerate(D):
    for m in range(-2,3):
        up,dn=idx(m,1),idx(m,-1)
        Sz[j,j]+=0.5*((up in occ)-(dn in occ))
        st,sg=apply_op([('cr',up),('an',dn)],occ)
        if st is not None: Sp[ind[st],j]+=sg
Sm=Sp.T
S2=Sz@Sz+0.5*(Sp@Sm+Sm@Sp)
np.savez('mats.npz',Hcf=Hcf,H2=H2,H4=H4,S2=S2,Sz=Sz)
print(n, np.allclose(H2,H2.T), np.allclose(Hcf,Hcf.T))
