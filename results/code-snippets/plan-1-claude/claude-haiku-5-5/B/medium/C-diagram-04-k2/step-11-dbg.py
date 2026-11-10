from run_d6 import *
H=Hee+build_Hcf(0.0)
M=H+100*S2
w,v=np.linalg.eigh(M)
Ss=np.array([np.real(v[:,i].conj()@S2@v[:,i]) for i in range(v.shape[1])])
Sval=np.round((-1+np.sqrt(1+4*Ss))/2).astype(int)
EH=w-100*Sval*(Sval+1)
for S in sorted(set(Sval)):
    ids=np.where(Sval==S)[0]
    print(S, len(ids), np.round(np.sort(EH[ids])[:30],6))
