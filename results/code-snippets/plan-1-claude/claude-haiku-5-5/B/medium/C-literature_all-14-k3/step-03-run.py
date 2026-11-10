from ts import *
import numpy as np
h=onebody()
# Racah: F2=49B+7C, F4=63C/5 ; V = F2*V2 + F4*V4 (+F0 const dropped)
V2=Vtensor(2); V4=Vtensor(4)
D,Hcf=build(7,h,np.zeros((N,)*4))
_,H2=build(7,np.zeros((N,N)),V2)
_,H4=build(7,np.zeros((N,N)),V4)
np.savez('mats.npz',Hcf=Hcf,H2=H2,H4=H4)
# S^2 matrix
def S2(D):
    # S^2 = Sz^2 + (S+S- + S-S+)/2 ; build via one-body operators
    n=len(D); ind={d:i for i,d in enumerate(D)}
    Sz=np.zeros((n,n)); Sp=np.zeros((n,n))
    for j,occ in enumerate(D):
        for m in range(-2,3):
            up,dn=idx(m,1),idx(m,-1)
            Sz[j,j]+=0.5*((up in occ)-(dn in occ))
            st,sg=apply_op([('cr',up),('an',dn)],occ)
            if st is not None: Sp[ind[st],j]+=sg
    Sm=Sp.T
    return Sz@Sz+0.5*(Sp@Sm+Sm@Sp)
np.save('S2.npy',S2(D))
print(len(D))
