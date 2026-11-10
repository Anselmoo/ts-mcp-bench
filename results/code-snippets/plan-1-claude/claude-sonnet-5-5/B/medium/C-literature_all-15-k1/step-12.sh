cd <SANDBOX_TMP> && python3 - <<'E'
import numpy as np
from d7 import *
sel=np.where(sz==0.5)[0]
Mtot=np.array([sum(so[i][0] for i in range(n) if (dets[k]>>i)&1) for k in sel])
Dq,B,C=889.6,915,3794
F2=B+C/7;F4=C/35
H=Dq*Md['cf']+49*F2*Md[2]+441*F4*Md[4]
w,V=np.linalg.eigh(H)
e0=lv(Dq,B,C)['q'][0]
R=np.exp(-1j*np.pi/2*Mtot)
i=0
while i<len(w):
    j=i
    while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
    chi=sum(np.vdot(V[:,k],R*V[:,k]) for k in range(i,j))
    if 3000<w[i]-e0<30000 or True: print(round(w[i]-e0),j-i,np.round(chi.real,2))
    i=j
E