
cd /tmp/tsbench-run-uqj8uf3b && cat << 'EOF' > run2.py
import numpy as np
from many import *
# L operators on spin-orbitals
def lop(sign):
    h=np.zeros((10,10),complex)
    for m in range(-2,2):
        pass
    return h
Lp=np.zeros((10,10),complex); Lm=np.zeros((10,10),complex); Lz=np.zeros((10,10),complex)
for m in range(-2,3):
    i=m+2
    for s in range(2):
        Lz[2*i+s,2*i+s]=m
        if m<2: Lp[2*(i+1)+s,2*i+s]=np.sqrt(6-m*(m+1))
        if m>-2: Lm[2*(i-1)+s,2*i+s]=np.sqrt(6-m*(m-1))
Mlz=build(Lz,np.zeros((10,)*4)); Mlp=build(Lp,np.zeros((10,)*4)); Mlm=build(Lm,np.zeros((10,)*4))
L2=Mlz@Mlz+0.5*(Mlp@Mlm+Mlm@Mlp)
np.save('L2.npy',L2[np.ix_(sec,sec)])
def classify(Dq,B,C):
    Hm=spectrum(Dq,B,C)
    S=Hm[np.ix_(sec,sec)]
    e,v=np.linalg.eigh(S)
    e6=np.linalg.eigvalsh(Hm[np.ix_(sec5,sec5)])[0]
    L2s=L2[np.ix_(sec,sec)]
    out=[]
    for k in range(len(e)):
        out.append((e[k]-e6, np.real(np.conj(v[:,k])@L2s@v[:,k])))
    return out
if __name__=="__main__":
    for E,L in classify(0.8,0.8,3.2): print(round(E,1), round(L,2))
EOF
python3 run2.py