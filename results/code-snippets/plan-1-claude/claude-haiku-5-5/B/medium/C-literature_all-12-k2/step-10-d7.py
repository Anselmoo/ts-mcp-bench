import numpy as np, itertools
from ff import build_V, build_h
from fock import hamiltonian
from scipy.optimize import least_squares
hb=build_h().real  # single-particle angular matrix (complex basis, real-valued here)
# check hermitian/real
hbc=build_h()
print("imag max",np.abs(hbc.imag).max())
hcf=np.zeros((10,10))
for i in range(5):
    for j in range(5):
        for s in (0,1):
            hcf[2*i+s,2*j+s]=6*hbc[i,j].real
V2=build_V({0:0.0,2:1.0,4:0.0})
V4=build_V({0:0.0,2:0.0,4:1.0})
N=7
basis=list(itertools.combinations(range(10),N))
Hcf,b=hamiltonian(N,hcf,np.zeros((10,)*4),basis)
H2,_=hamiltonian(N,np.zeros((10,10)),V2,basis)
H4,_=hamiltonian(N,np.zeros((10,10)),V4,basis)
np.savez('d7mats.npz',Hcf=Hcf.real,H2=H2.real,H4=H4.real,basis=np.array(basis))
print("saved", Hcf.shape, np.abs(Hcf.imag).max(), np.abs(H2.imag).max())
