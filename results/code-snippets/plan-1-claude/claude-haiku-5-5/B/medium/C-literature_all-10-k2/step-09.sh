python3 -c "
import ligand as M, numpy as np
print('imag max', np.abs(M.cf_one_body(1.0).imag).max())
b=M.det_basis(6)
S2,Sz,Sp=M.S2_matrix(b)
# singlet subspace: S2 eigenvalue 0
w,v=np.linalg.eigh(S2); Q=v[:,np.abs(w)<1e-8]
print('singlet dim', Q.shape[1])
B=1.0; C=4.5; F2=49*B+7*C; F4=63*C/5
for x in [0.0,1.0,2.0,3.0,3.5]:
    H=M.hamiltonian(F2,F4,x,b)
    Hs=Q.T@H@Q
    ev=np.linalg.eigvalsh(Hs)
    ev=ev-ev[0]
    vals=np.round(ev,4)
    u,c=np.unique(vals,return_counts=True)
    print('x=',x, list(zip(u[:12],c[:12])))
"