cd . && sed -i 's/S2=Sp.T@Sp + np.diag(Sz\*\*2) - np.diag(Sz).*/S2=Sp.T@Sp + np.diag(Sz**2) + np.diag(Sz)/' ligand.py && python3 -c "
import ligand as L, numpy as np
# trace checks
print('trace k2 full d-shell', np.trace(L.T[2].reshape(25,25)))
# d2 free ion test: F2,F4 from B,C with C=4.5B; B=1
B=1.0; C=4.5
F4=441*C/35; F2=49*B+7*C
# Racah check: F4 = 63C/5 ; F2 = 49B+7C
F4=63*C/5
b2=L.det_basis(2)
import ligand as M
H=M.hamiltonian(F2,F4,0.0,b2)
S2,Sz,Sp=M.S2_matrix(b2)
# restrict to Sz=1 (triplet) and Sz=0 singlets
ev,vec=np.linalg.eigh(H)
print('d2 free-ion levels (cm-1 units of B):')
print(np.round(ev-ev[0],3))
"