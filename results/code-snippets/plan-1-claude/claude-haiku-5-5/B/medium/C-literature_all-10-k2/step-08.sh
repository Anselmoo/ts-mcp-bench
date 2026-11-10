python3 -c "
import ligand as M, numpy as np
b2=M.det_basis(2)
def lev(F2,F4):
    H=M.hamiltonian(F2,F4,0.0,b2); ev=np.linalg.eigvalsh(H); return np.round(ev-ev[0],3)
for B,C in [(1,0),(1,4.5),(0,1),(1,1)]:
    F2=49*B+7*C; F4=63*C/5
    e=lev(F2,F4)
    print(B,C, sorted(set(e)))
"