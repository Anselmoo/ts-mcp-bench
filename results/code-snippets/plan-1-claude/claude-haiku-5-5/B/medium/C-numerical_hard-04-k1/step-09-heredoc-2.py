exec(open('/tmp/run_d5.py').read())
H=H_of(1000,500,2200)
print("herm",np.allclose(H,H.conj().T))
w,U=np.linalg.eigh(S2)
print("S2 eigen counts", [ (round(x,2),int(np.sum(np.abs(w-x)<1e-6))) for x in np.unique(np.round(w,4))])
P=U[:,np.abs(w-0.75)<1e-6]
ev=np.linalg.eigvalsh(P.conj().T@H@P)
print(np.round(ev[:12],2))
print("full H lowest", np.round(np.linalg.eigvalsh(H)[:10],2))
