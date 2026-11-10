import numpy as np, sys
sys.path.insert(0,'.')
from d4 import *
# rotations
ops={'E':np.eye(D),
     'C3':rot((1,1,1),2*np.pi/3),
     'C2z':rot((0,0,1),np.pi),
     'C4z':rot((0,0,1),np.pi/2),
     "C2'":rot((1,0,0),np.pi)}
cls=['E','C3','C2z','C4z',"C2'"]; csz=[1,8,3,6,6]
chartab={'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
# check commutation
print('comm check', max(np.abs(ops['C4z']@Hee-Hee@ops['C4z']).max(),0))
# S^2 eigenspaces
s2w,s2v=eigh((S2+S2.conj().T)/2)
def term_list(Dq_cm):
    H=Hee+Dq_cm*Hcf
    res=[]
    for S in (0,1,2):
        sel=np.abs(s2w-S*(S+1))<1e-6
        V=s2v[:,sel]
        if V.shape[1]==0: continue
        HS=V.conj().T@H@V
        ev,evec=eigh((HS+HS.conj().T)/2)
        W_all=V@evec
        # cluster
        i=0
        while i<len(ev):
            j=i
            while j+1<len(ev) and abs(ev[j+1]-ev[i])<1e-5: j+=1
            Wc=W_all[:,i:j+1]
            chi=[np.trace(Wc.conj().T@ops[c]@Wc).real for c in cls]
            # multiplicities
            dec={}
            for name,ct in chartab.items():
                n=sum(csz[k]*chi[k]*ct[k] for k in range(5))/24
                if abs(n)>1e-6: dec[name]=round(n.real)
            res.append((ev[i],2*S+1,dec,j-i+1))
            i=j+1
    res.sort()
    return res
for Dqb in (0.90,2.15,3.35):
    Dq=Dqb*B/ 1.0  # Dq in cm^-1 = Dq/B * B
    tl=term_list(Dq)
    E0=tl[0][0]
    print(f"Dq/B={Dqb}  Dq={Dq:.1f} cm-1")
    for e,mult,dec,dg in tl[:8]:
        print(f"   E/B={(e-E0)/B:9.4f}  mult={mult}  irreps={dec}  dim={dg}")
