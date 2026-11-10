import numpy as np, pickle
H1,Hk,states,Sp=pickle.load(open('mats.pkl','rb'))
Sz=np.array([sum((1 if x%2==0 else -1) for x in st)/2 for st in states])
S2=Sp.conj().T@Sp+np.diag(Sz*Sz+Sz)
w,v=np.linalg.eigh(S2); T=v[:,np.abs(w-2)<1e-6]
for F2,F4 in [(1,0),(0,1)]:
    H=F2*Hk[2]+F4*Hk[4]
    Ht=T.conj().T@H@T
    print(F2,F4,np.unique(np.round(np.linalg.eigvalsh(Ht),4),return_counts=True))
