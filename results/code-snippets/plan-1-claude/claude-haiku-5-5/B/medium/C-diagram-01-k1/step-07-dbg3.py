exec(open('ts.py').read().split("csz=[")[0].replace("for k in ckeys: assert","#"))
Dm=Dmat(classes['C3'][0])
Vt=np.einsum('pqrs,pa,qb,rc,sd->abcd',V,Dm.T if False else np.kron(Dm,np.eye(2)),np.kron(Dm,np.eye(2)),np.kron(Dm,np.eye(2)),np.kron(Dm,np.eye(2)))
print(np.abs(Vt-V).max(), np.abs(V).max())
# check orbital function invariance: Vorb symmetry
Vr=np.einsum('pqrs,pa,qb,rc,sd->abcd',Vorb,Dm,Dm,Dm,Dm); print(np.abs(Vr-Vorb).max())
