from ts import *
F2,F4=1.0,0.6
G=coulomb_tensor({0:0.0,2:F2,4:F4})
states,idx,H=build_H(2,np.zeros((10,10)),G)
S2=spin_S2(2)
w,v=np.linalg.eigh(H+100*S2)
B=(9*F2-5*F4)/441; C=35*F4/441
out=[]
for e,vec in zip(w,v.T):
    S=(-1+np.sqrt(1+4*np.real(vec.conj()@S2@vec)))/2
    out.append((round(e-100*S*(S+1),6),round(S,2)))
import collections
c=collections.Counter(out)
for k in sorted(c): print(k,c[k])
print("B",B,"C",C)
